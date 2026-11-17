import asyncio
import copy
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.app.config import Settings, ROOT
from backend.app.main import create_app
from backend.app.errors import AppError
from backend.app.providers import Providers, board_id, chunk_source, retrieve
from backend.app.services import Services, valid_steps, deadline, selected_ids, normalize_citations
from backend.app.store import Store, Context
from backend.app.documents import extract_document

def configuration(tmp_path, live=False):
    return Settings(mode='live' if live else 'demo', data_dir=tmp_path, environment='development',
        supabase_url='https://project.supabase.co', supabase_key='sb_publishable_test', gemini_key='test-gemini-secret',
        miro_token='test-miro-secret', miro_users={'user'}, miro_boards={'test-board'})

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(configuration(tmp_path))) as client:
        yield client

def test_full_workspace_workflow(client):
    workspace = client.get('/api/workspace').json()
    assert len(workspace['sources']) >= 6
    source = client.post('/api/sources', json={'title': 'Pilot research', 'text': 'Pilot research requires accessibility testing and a named launch owner.'}).json()['source']
    answer = client.post('/api/chat', json={'question': 'Who owns accessibility?', 'sourceIds': [source['id']]}).json()
    assert answer['citations'] and {c['sourceId'] for c in answer['citations']} == {source['id']}
    follow = client.post('/api/chat', json={'question': 'Summarize accessibility', 'sourceIds': [source['id']], 'conversationId': answer['conversation']['id']})
    assert len(follow.json()['conversation']['messages']) == 4
    assert client.post('/api/insights', json={}).status_code == 200
    client.post('/api/sources', json={'title': 'Additional evidence', 'text': 'Accessibility checks need a pilot cohort and a named researcher.'})
    assert client.get('/api/workspace').json()['insightsStale']
    plan = client.post('/api/plans', json={'sourceIds': [source['id']]}).json()['plan']
    plan['steps'][0].update({'owner': 'Research team', 'deadline': '2026-11-05'})
    assert client.post('/api/plans/update', json={'id': plan['id'], 'steps': plan['steps']}).status_code == 200
    assert client.post('/api/publish', json={'id': plan['id'], 'approved': False}).status_code == 400
    assert client.post('/api/publish', json={'id': plan['id'], 'approved': True}).json()['demo']
    assert client.post('/api/comments', json={'targetId': source['id'], 'text': 'Review pilot evidence'}).status_code == 200
    assert client.post('/api/comments', json={'targetId': 'other-workspace', 'text': 'No'}).status_code == 400
    assert client.post('/api/tasks', json={'title': 'Validate pilot', 'owner': 'Design', 'deadline': '2026-11-05'}).status_code == 200
    task = client.get('/api/workspace').json()['tasks'][0]
    assert client.post('/api/tasks/update', json={'id': task['id'], 'done': True}).status_code == 200
    assert client.post('/api/settings', json={'autoSync': True, 'intervalMinutes': 1}).status_code == 200
    assert client.post('/api/sync', json={}).status_code == 200
    client.post('/api/chat', json={'question': 'What is the pilot plan?', 'sourceIds': [source['id']]})
    assert client.get('/api/team').json()['members']
    assert client.post('/api/team/invite', json={}).status_code == 403
    assert client.post('/api/team/rename', json={'name': 'Research studio'}).status_code == 200
    assert client.post('/api/conversations/delete', json={'id': answer['conversation']['id']}).status_code == 200
    assert answer['conversation']['id'] not in {c['id'] for c in client.get('/api/workspace').json()['conversations']}
    chunks_before_delete = client.get('/api/workspace').json()['chunkCount']
    assert client.post('/api/sources/delete', json={'id': source['id']}).status_code == 200
    removed = client.get('/api/workspace').json()
    assert source['id'] not in {s['id'] for s in removed['sources']}
    assert removed['chunkCount'] == chunks_before_delete - 1
    assert not removed['conversations']

def test_production_disables_demo_and_documentation(tmp_path):
    demo = configuration(tmp_path)
    demo.environment = 'production'
    with pytest.raises(RuntimeError, match='Demo mode'):
        demo.validate()
    live = configuration(tmp_path, True)
    live.environment = 'production'
    live.origins = {'https://mirova.example'}
    with TestClient(create_app(live)) as client:
        assert client.get('/api/health').json()['backend'] == 'fastapi'
        assert client.get('/api/docs').status_code == 404
        assert client.get('/api/openapi.json').status_code == 404
        assert client.get('/api/workspace').status_code == 401

def test_bounds_origins_validation_and_secrets(client):
    assert client.get('/api/workspace', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.post('/api/tasks', json={'title': 'Bad date', 'deadline': '2026-02-31'}).status_code == 400
    assert client.post('/api/chat', json={'question': 'What?', 'sourceIds': ['unknown']}).status_code == 400
    assert client.post('/api/chat', content='[' , headers={'Content-Type': 'application/json'}).status_code == 400
    assert client.post('/api/sources', json={'title': 'x', 'text': 'a' * 2000001}).status_code == 413
    assert client.post('/api/sync', content='{}').status_code == 415
    config = client.get('/api/config')
    assert config.headers['cache-control'] == 'no-store'
    assert 'test-gemini-secret' not in config.text and 'test-miro-secret' not in config.text
    assert config.json()['key'] == 'sb_publishable_test'
    for phase in [{}, [], None, 'wrong']:
        with pytest.raises(AppError):
            valid_steps([{'title': 't', 'description': 'd', 'phase': phase}])
    assert deadline('2028-02-29') == '2028-02-29'
    production = configuration(ROOT / '.data', True)
    production.environment = 'production'
    production.origins = {'http://localhost:3000'}
    with pytest.raises(RuntimeError, match='ALLOWED_ORIGINS'):
        production.validate()

def test_grouped_citations_become_clickable_and_unknown_ids_are_rejected():
    assert normalize_citations('Evidence [1, 2] and [3].', 3) == 'Evidence [1] [2] and [3].'
    for answer in ['Evidence [1, 99].', 'No sources', 'Evidence [0]', 'Unsupported range [1-5]']:
        with pytest.raises(AppError, match='valid source citations'):
            normalize_citations(answer, 3)

def test_document_formats_and_archive_limits():
    for extension in ['pdf', 'docx']:
        fixture = Path(__file__).parent / 'fixtures' / ('research.' + extension)
        assert len(extract_document(fixture.name, fixture.read_bytes())['text']) > 10
    assert 'accessibility' in extract_document('research.md', b'Validate accessibility before launch')['text']
    for filename, content in [('bad.pdf', b'fake'), ('bad.docx', b'PKbad'), ('old.doc', b'bad'), ('empty.txt', b'')]:
        with pytest.raises(AppError):
            extract_document(filename, content)
    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('word/document.xml', b'x' * (21 * 1024 * 1024))
    with pytest.raises(AppError, match='expands'):
        extract_document('large.docx', bomb.getvalue())

def test_http_document_parser_isolated_process(client):
    for extension in ['pdf', 'docx']:
        file = Path(__file__).parent / 'fixtures' / ('research.' + extension)
        response = client.post('/api/upload', files={'file': (file.name, file.read_bytes())}, data={'title': 'Imported research'})
        assert response.status_code == 200, response.text
        assert response.json()['source']['title'] == 'Imported research'

@pytest.mark.asyncio
async def test_auth_jwt_forwarding_membership_and_cas(tmp_path):
    user, outsider = 'a2c13a5b-dfd4-4531-94c0-3f460909ed8f', 'b2c13a5b-dfd4-4531-94c0-3f460909ed8f'
    calls = []
    def upstream(request):
        calls.append(request)
        assert request.headers['apikey'] == 'sb_publishable_test'
        assert request.headers['authorization'] == 'Bearer user-jwt'
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': user, 'email': 'research@example.com'})
        if request.url.path == '/rest/v1/team_members':
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[])
    settings = configuration(tmp_path, True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
        store = Store(settings, http, None)
        from starlette.requests import Request
        request = Request({'type': 'http', 'headers': [(b'authorization', b'Bearer user-jwt')]})
        ctx = await store.context(request)
        assert ctx.user_id == user
        bad = Request({'type': 'http', 'headers': [(b'authorization', b'Bearer user-jwt'), (b'x-workspace-id', outsider.encode())]})
        with pytest.raises(AppError, match='access denied'):
            await store.context(bad)
        ctx.exists = True
        with pytest.raises(AppError) as error:
            await store.write(ctx, {'sources': [], 'chunks': []})
        assert error.value.status == 409
        unauthorized = Request({'type': 'http', 'headers': []})
        with pytest.raises(AppError) as error:
            await store.context(unauthorized)
        assert error.value.status == 401

@pytest.mark.asyncio
async def test_supabase_source_save_rpc_clears_deleted_vectors(tmp_path):
    calls = []
    def upstream(request):
        calls.append(request)
        assert request.headers['apikey'] == 'sb_publishable_test'
        assert request.headers['authorization'] == 'Bearer user-jwt'
        return httpx.Response(200, json=5)
    settings = configuration(tmp_path, True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
        store = Store(settings, http, None)
        ctx = Context('user', 'user', 'Research', 'user-jwt', revision=4, exists=True,
            pending=[{'sourceId': 'miro-board', 'chunks': []}])
        await store.write(ctx, {'sources': [], 'chunks': [], 'plans': [], 'activity': []})
    request = calls[0]
    assert request.url.path.endswith('/rest/v1/rpc/save_workspace_sources')
    body = json.loads(request.content)
    assert body['p_expected_revision'] == 4
    assert body['p_sources'] == [{'sourceId': 'miro-board', 'chunks': []}]
    assert body['p_data']['chunks'] == []
    assert ctx.revision == 5 and ctx.pending == []

@pytest.mark.asyncio
async def test_miro_http_boundary_uses_bearer_token_and_redacts_errors(tmp_path):
    calls = []
    def upstream(request):
        calls.append(request)
        return httpx.Response(200, json={'data': [], 'cursor': None})
    settings = configuration(tmp_path, True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
        provider = Providers(settings, http)
        assert await provider.miro('boards/test-board/items?limit=50') == {'data': [], 'cursor': None}
    assert calls[0].url == 'https://api.miro.com/v2/boards/test-board/items?limit=50'
    assert calls[0].headers['authorization'] == 'Bearer test-miro-secret'

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(401, text='sensitive-provider-body'))) as http:
        with pytest.raises(AppError) as error:
            await Providers(settings, http).miro('boards/test-board')
    assert error.value.status == 502
    assert 'sensitive-provider-body' not in error.value.message

def test_live_miro_sync_route_calls_miro_gemini_and_supabase(tmp_path):
    calls = []
    workspace = {'sources': [], 'plans': [], 'activity': [], 'chunks': []}
    def upstream(request):
        calls.append(request)
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': 'a2c13a5b-dfd4-4531-94c0-3f460909ed8f', 'email': 'research@example.com'})
        if request.url.path == '/rest/v1/workspaces':
            return httpx.Response(200, json=[{'data': workspace, 'revision': 1}])
        if request.url.path == '/v2/boards/test-board':
            return httpx.Response(200, json={'name': 'Pilot board'})
        if request.url.path == '/v2/boards/test-board/items':
            assert request.url.params['limit'] == '50'
            return httpx.Response(200, json={'data': [{'id': 'item-1', 'type': 'sticky_note', 'data': {'content': 'Validate the pilot'}}]})
        if request.url.host == 'generativelanguage.googleapis.com':
            return httpx.Response(200, json={'embedding': {'values': [0.] * 768}})
        if request.url.path == '/rest/v1/rpc/save_workspace_sources':
            body = json.loads(request.content)
            workspace.update(body['p_data'])
            assert body['p_sources'][0]['sourceId'] == 'miro-test-board'
            assert len(body['p_sources'][0]['chunks'][0]['embedding']) == 768
            return httpx.Response(200, json=2)
        raise AssertionError(f'Unexpected upstream request: {request.method} {request.url.path}')

    settings = configuration(tmp_path, True)
    settings.miro_users = {'a2c13a5b-dfd4-4531-94c0-3f460909ed8f'}
    app = create_app(settings, transport=httpx.MockTransport(upstream))
    with TestClient(app) as client:
        response = client.post('/api/sync', headers={'Authorization': 'Bearer user-jwt'}, json={'board': 'test-board'})
    assert response.status_code == 200, response.text
    assert response.json()['source']['id'] == 'miro-test-board'
    assert {call.url.host for call in calls} >= {'api.miro.com', 'generativelanguage.googleapis.com', 'project.supabase.co'}
    assert all(call.headers['authorization'] == 'Bearer user-jwt' for call in calls if call.url.host == 'project.supabase.co')
    assert all(call.headers['authorization'] == 'Bearer test-miro-secret' for call in calls if call.url.host == 'api.miro.com')

@pytest.mark.asyncio
async def test_sync_pagination_incremental_and_allowlists(tmp_path):
    settings = configuration(tmp_path, True)
    provider = AsyncMock()
    provider.embed.return_value = [0.] * 768
    http = httpx.AsyncClient()
    store = Store(settings, http, provider)
    services = Services(settings, store, provider)
    ctx = Context('user', 'user', 'Research')
    workspace = {'sources': [], 'chunks': [], 'plans': [], 'activity': []}
    provider.miro.side_effect = [{'name': 'Live board'}, {'data': [{'id': '1', 'type': 'sticky_note', 'data': {'content': '<p>Validate pilot</p>'}}], 'cursor': 'next'}, {'data': [{'id': '2', 'type': 'shape', 'data': {'content': 'Assign owner'}}]}]
    assert (await services.sync_board(ctx, workspace, 'test-board'))['changed'] == 1
    assert len(ctx.pending) == 1
    provider.miro.side_effect = [{'name': 'Live board'}, {'data': [{'id': '2', 'type': 'shape', 'data': {'content': 'Assign owner'}}, {'id': '1', 'type': 'sticky_note', 'data': {'content': '<p>Validate pilot</p>'}}]}]
    assert (await services.sync_board(ctx, workspace, 'test-board'))['changed'] == 0
    provider.miro.side_effect = [{'name': 'Live board'}, {'data': [], 'cursor': 'same'}, {'data': [], 'cursor': 'same'}]
    with pytest.raises(AppError, match='repeated'):
        await services.sync_board(ctx, workspace, 'test-board')
    with pytest.raises(AppError) as error:
        services.authorize_miro(Context('other', 'other', 'Other'), 'test-board')
    assert error.value.status == 403
    with pytest.raises(AppError):
        services.authorize_miro(ctx, 'another-board')
    provider.miro.side_effect = [{'name': 'Large board'}] + [{'data': [], 'cursor': f'cursor-{i}'} for i in range(10)]
    with pytest.raises(AppError, match='500-item sync limit'):
        await services.sync_board(ctx, workspace, 'test-board')
    provider.miro.side_effect = [{'name': 'Oversized page'}, {'data': [{'id': str(i), 'data': {'content': 'x'}} for i in range(501)]}]
    with pytest.raises(AppError, match='500-item sync limit'):
        await services.sync_board(ctx, workspace, 'test-board')
    assert board_id('https://miro.com/app/board/test-board%3D/') == 'test-board='
    for value in ['https://evil.example/board/hello', '../admin', {}, 'http://localhost']:
        with pytest.raises(AppError):
            board_id(value)
    await http.aclose()

@pytest.mark.asyncio
async def test_source_count_and_total_text_caps(tmp_path):
    store = Store(configuration(tmp_path), None, None)
    ctx = Context('local-demo', 'local-demo', 'Research')
    full = {'sources': [{'id': str(i), 'text': 'x'} for i in range(100)], 'chunks': []}
    with pytest.raises(AppError, match='source limit'):
        await store.index(ctx, full, {'id': 'new', 'text': 'new'})
    large = {'sources': [{'id': 'large', 'text': 'x' * 2_000_000}], 'chunks': []}
    with pytest.raises(AppError, match='source limit'):
        await store.index(ctx, large, {'id': 'next', 'text': 'x'})

@pytest.mark.asyncio
async def test_malformed_model_output_and_citations(tmp_path):
    settings = configuration(tmp_path, True)
    provider = AsyncMock()
    store = Store(settings, None, provider)
    services = Services(settings, store, provider)
    workspace = {'sources': [{'id': 'a', 'title': 'A', 'text': 'a', 'tags': []}, {'id': 'b', 'title': 'B', 'text': 'b', 'tags': []}], 'plans': [], 'chunks': []}
    provider.generate.return_value = json.dumps({'themes': [None, 3, {'label': 'Pilot', 'summary': 'Proposed theme', 'sourceIds': ['a']}], 'gaps': [None, 5], 'conflicts': [{'title': 'Unsupported', 'description': 'Only one source', 'sourceIds': ['a']}]})
    insights = await services.analyze(workspace)
    assert len(insights['themes']) == 1 and not insights['conflicts'] and not insights['gaps']
    store.read = AsyncMock(return_value=copy.deepcopy(workspace))
    store.db = AsyncMock(return_value=[{'id': 'c', 'source_id': 'a', 'content': 'Evidence', 'similarity': .8}])
    provider.embed.return_value = [0.] * 768
    provider.generate.return_value = 'Invented citation [99]'
    with pytest.raises(AppError, match='valid source citations'):
        await services.chat(Context('user', 'user', 'Research'), {'question': 'What is known?'})

@pytest.mark.asyncio
async def test_provider_errors_are_redacted(tmp_path):
    settings = configuration(tmp_path, True)
    for response in [httpx.Response(200, json={'candidates': [None]}), httpx.Response(403, text='provider-secret-response')]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: response)) as http:
            provider = Providers(settings, http)
            with pytest.raises(AppError) as error:
                await provider.generate('test')
            assert 'provider-secret-response' not in error.value.message

@pytest.mark.asyncio
async def test_publication_durable_resume_cas_and_uncertain_block(tmp_path):
    settings = configuration(tmp_path, True)
    provider = AsyncMock()
    store = Store(settings, None, provider)
    ctx = Context('user', 'user', 'Research')
    plan = {'id': 'plan', 'status': 'draft', 'steps': valid_steps([{'title': 'Pilot', 'description': 'Validate', 'phase': 'Discover', 'owner': 'A <B>'}, {'title': 'Launch', 'description': 'Measure', 'phase': 'Launch'}])}
    saved = {'sources': [], 'plans': [copy.deepcopy(plan)], 'chunks': []}
    store.read = AsyncMock(side_effect=lambda _: copy.deepcopy(saved))
    conflicts = [True]
    async def write(_, value):
        if conflicts:
            conflicts.pop()
            raise AppError('Workspace changed while saving', 409)
        saved.update(copy.deepcopy(value))
    store.write = AsyncMock(side_effect=write)
    calls = []
    async def remote(path, method, body):
        calls.append((path, body))
        return {'id': f'item-{len(calls)}'}
    provider.miro.side_effect = remote
    service = Services(settings, store, provider)
    await service.publish(ctx, saved, plan, 'test-board')
    assert len(calls) == 3 and plan['status'] == 'published'
    assert 'A &lt;B&gt;' in calls[0][1]['data']['content']
    restarted = copy.deepcopy(saved['plans'][0])
    await Services(settings, store, provider).publish(ctx, saved, restarted, 'test-board')
    assert len(calls) == 3
    failing = copy.deepcopy(plan)
    failing.update({'id': 'uncertain', 'status': 'draft', 'publishedItemIds': [], 'publishedConnectorIds': []})
    saved['plans'].append(copy.deepcopy(failing))
    provider.miro.side_effect = AppError('Miro connection failed', 502)
    with pytest.raises(AppError):
        await service.publish(ctx, saved, failing, 'test-board')
    count = provider.miro.await_count
    with pytest.raises(AppError, match='uncertain outcome'):
        await service.publish(ctx, saved, failing, 'test-board')
    assert provider.miro.await_count == count

@pytest.mark.asyncio
async def test_per_workspace_lock_does_not_block_other_workspaces(tmp_path):
    store = Store(configuration(tmp_path), None, None)
    async with store.locked('workspace-a'):
        async with asyncio.timeout(.1):
            async with store.locked('workspace-b'):
                pass
    assert not store.locks
