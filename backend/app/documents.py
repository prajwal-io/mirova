import io
import zipfile
from pathlib import Path
from defusedxml import ElementTree
from pypdf import PdfReader
from .errors import AppError

def extract_document(name, content):
    if len(content) > 10 * 1024 * 1024:
        raise AppError('File is too large. Limit: 10 MB.', 413)
    extension = Path(name).suffix.lower()
    try:
        if extension == '.pdf':
            if not content.startswith(b'%PDF-'):
                raise AppError('This file is not a valid PDF.')
            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                raise AppError('Remove the PDF password before importing.')
            if len(reader.pages) > 200:
                raise AppError('PDFs are limited to 200 pages.')
            parts = []
            for page in reader.pages:
                # Guard common decompression bombs before text extraction.
                if len(page.get_contents().get_data() if page.get_contents() else b'') > 20 * 1024 * 1024:
                    raise AppError('PDF page exceeds the processing limit.')
                parts.append(page.extract_text() or '')
                if sum(map(len, parts)) > 200000:
                    raise AppError('Document exceeds 200,000 extracted characters.')
            text = '\n\n'.join(parts)
        elif extension == '.docx':
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 2000 or sum(e.file_size for e in entries) > 50 * 1024 * 1024 or any(e.file_size > 20 * 1024 * 1024 for e in entries):
                    raise AppError('Word document expands beyond the processing limit.')
                root = ElementTree.fromstring(archive.read('word/document.xml'))
                ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
                text = '\n'.join(''.join(p.itertext()) for p in root.iter(ns + 'p'))
        elif extension in {'.txt', '.md', '.csv'}:
            text = content.decode('utf-8-sig')
        else:
            raise AppError('Choose PDF, DOCX, TXT, Markdown, or CSV. Save legacy .doc as .docx.')
    except AppError:
        raise
    except Exception:
        raise AppError('Document is damaged or unsupported. Save a fresh copy and retry.') from None
    text = text.replace('\x00', '').strip()
    if len(text) < 10:
        raise AppError('No readable text found. Scanned PDFs need OCR before uploading.')
    if len(text) > 200000:
        raise AppError('Document exceeds 200,000 extracted characters. Split it into smaller files.')
    return {'title': Path(name).stem[:160], 'text': text}
