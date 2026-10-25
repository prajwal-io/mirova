import asyncio
import copy
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4
import httpx
from .config import Settings
from .errors import AppError
from .providers import chunk_source, fingerprint

@dataclass
class Context:
    user_id: str
    workspace_id: str
    label: str
    token: str = ''
    revision: int = 0
    exists: bool = False
    pending: list = field(default_factory=list)

class Store:
    def __init__(self, settings: Settings, client: httpx.AsyncClient, providers):
        self.settings, self.client, self.providers = settings, client, providers
        self.locks = {}

    @asynccontextmanager
    async def locked(self, workspace):
        # Reference counts allow safe cleanup after the last queued request.
        entry = self.locks.setdefault(workspace, [asyncio.Lock(), 0])
        entry[1] += 1
        try:
            async with entry[0]:
                yield
        finally:
            entry[1] -= 1
            if not entry[1]:
                self.locks.pop(workspace, None)

    async def db(self, ctx, path, method='GET', body=None, params=None):
        try:
            response = await self.client.request(method, f'{self.settings.supabase_url}/{path}',
                headers={'apikey': self.settings.supabase_key, 'Authorization': f'Bearer {ctx.token}', 'Prefer': 'return=representation'},
                json=body, params=params, timeout=25)
        except httpx.HTTPError:
            raise AppError('Database connection unavailable. Please retry.', 503) from None
        if not response.is_success:
            if response.status_code == 401:
                raise AppError('Unauthorized', 401)
            if response.status_code == 403:
                raise AppError('Workspace access denied', 403)
            if response.status_code == 409 or 'changed while saving' in response.text:
                raise AppError('Workspace changed while saving. Refresh and retry.', 409)
            raise AppError('Database operation failed. Check the schema and permissions.', 502)
        return response.json() if response.content else None

    async def context(self, request):
        if not self.settings.live:
            return Context('local-demo', 'local-demo', 'Local teammate')
        auth = request.headers.get('authorization', '')
        if not auth.startswith('Bearer ') or len(auth) > 8192:
            raise AppError('Unauthorized', 401)
        ctx = Context('', '', '', auth[7:])
        user = await self.db(ctx, 'auth/v1/user')
        if not isinstance(user, dict) or not user.get('id'):
            raise AppError('Unauthorized', 401)
        ctx.user_id, ctx.label = user['id'], user.get('email') or 'Teammate'
        ctx.workspace_id = request.headers.get('x-workspace-id') or ctx.user_id
        try:
            UUID(ctx.workspace_id)
        except ValueError:
            raise AppError('Invalid workspace.') from None
        if ctx.workspace_id != ctx.user_id:
            members = await self.db(ctx, 'rest/v1/team_members', params={'select': 'user_id', 'workspace_id': f'eq.{ctx.workspace_id}', 'user_id': f'eq.{ctx.user_id}'})
            if not members:
                raise AppError('Workspace access denied', 403)
        return ctx

    async def read(self, ctx):
        if self.settings.live:
            rows = await self.db(ctx, 'rest/v1/workspaces', params={'select': 'data,revision', 'user_id': f'eq.{ctx.workspace_id}'})
            ctx.exists = bool(rows)
            ctx.revision = rows[0]['revision'] if rows else 0
            return rows[0]['data'] if rows else {'sources': [], 'chunks': [], 'plans': [], 'activity': []}
        file = self.settings.data_dir / 'workspace.json'
        if file.exists():
            return json.loads(await asyncio.to_thread(file.read_text, encoding='utf8'))
        seed = json.loads(Path(__file__).with_name('seed.json').read_text(encoding='utf8'))
        seed['chunks'] = [c for s in seed['sources'] for c in chunk_source(s)]
        await self.write(ctx, seed)
        return seed

    async def write(self, ctx, workspace):
        if self.settings.live:
            data = {**workspace, 'chunks': []}
            if ctx.pending:
                revision = await self.db(ctx, 'rest/v1/rpc/save_workspace_sources', 'POST', {
                    'p_workspace_id': ctx.workspace_id, 'p_expected_revision': ctx.revision if ctx.exists else -1,
                    'p_data': data, 'p_sources': ctx.pending})
                ctx.revision, ctx.exists, ctx.pending = revision, True, []
                return
            row = {'data': data, 'revision': ctx.revision + 1}
            if ctx.exists:
                rows = await self.db(ctx, 'rest/v1/workspaces', 'PATCH', row,
                    {'user_id': f'eq.{ctx.workspace_id}', 'revision': f'eq.{ctx.revision}'})
            else:
                rows = await self.db(ctx, 'rest/v1/workspaces', 'POST', {**row, 'user_id': ctx.workspace_id})
            if not rows:
                raise AppError('Workspace changed while saving. Refresh and retry.', 409)
            ctx.revision, ctx.exists = row['revision'], True
            return
        await asyncio.to_thread(self.atomic_json, self.settings.data_dir / 'workspace.json', workspace)

    @staticmethod
    def atomic_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + f'.{uuid4()}.tmp')
        with temp.open('w', encoding='utf8') as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)

    async def index(self, ctx, workspace, source):
        previous = next((s for s in workspace['sources'] if s['id'] == source['id']), None)
        source['hash'] = fingerprint(source['text'])
        if previous and previous.get('hash') == source['hash']:
            return False
        chunks = chunk_source(source)
        if self.settings.live:
            semaphore = asyncio.Semaphore(4)
            async def vector(chunk):
                async with semaphore:
                    return {'id': chunk['id'], 'content': chunk['content'], 'embedding': await self.providers.embed(chunk['content'])}
            vectors = await asyncio.gather(*(vector(c) for c in chunks))
            ctx.pending.append({'sourceId': source['id'], 'chunks': vectors})
        workspace['sources'] = [s for s in workspace['sources'] if s['id'] != source['id']] + [source]
        workspace['chunks'] = [c for c in workspace.get('chunks', []) if c['sourceId'] != source['id']] + chunks
        return True
