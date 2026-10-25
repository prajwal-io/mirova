"""Short-lived parser child: hard timeout on all OSes and resource caps on Linux."""
import asyncio
import multiprocessing
import os
from .errors import AppError

def _extract(connection, name, content):
    try:
        if os.name != 'nt':
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
        import pypdf
        # Configure bounded decompression before any PDF streams are expanded.
        pypdf.overwrite_configuration(zlib_maximum_output_length=20 * 1024 * 1024)
        from .documents import extract_document
        connection.send({'result': extract_document(name, content)})
    except AppError as error:
        connection.send({'error': error.message, 'status': error.status})
    except BaseException:
        connection.send({'error': 'Document exceeds processing limits or is damaged.', 'status': 400})
    finally:
        connection.close()

class DocumentParser:
    def __init__(self):
        self.slots = asyncio.Semaphore(1)

    async def extract(self, name, content):
        if len(content) > 10 * 1024 * 1024:
            raise AppError('File is too large. Limit: 10 MB.', 413)
        async with self.slots:
            spawn = multiprocessing.get_context('spawn')
            reader, writer = spawn.Pipe(duplex=False)
            process = spawn.Process(target=_extract, args=(writer, name, content), daemon=True)
            process.start()
            writer.close()
            try:
                for _ in range(300):
                    if reader.poll():
                        try:
                            message = reader.recv()
                        except EOFError:
                            raise AppError('Document parser exceeded its processing limit.') from None
                        if 'error' in message:
                            raise AppError(message['error'], message['status'])
                        return message['result']
                    if not process.is_alive():
                        raise AppError('Document parser exceeded its processing limit.')
                    await asyncio.sleep(.1)
                raise AppError('Document processing timed out. Split it into smaller files.', 408)
            finally:
                if process.is_alive():
                    process.terminate()
                await asyncio.to_thread(process.join, 3)
                if process.is_alive():
                    process.kill()
                    await asyncio.to_thread(process.join, 3)
                reader.close()
