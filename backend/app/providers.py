import asyncio
import hashlib
import html
import math
import re
from urllib.parse import urlparse, unquote
import httpx
from .config import Settings
from .errors import AppError

def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()

def board_id(value):
    if not isinstance(value, str):
        raise AppError('Enter a valid Miro board ID or URL.')
    value = value.strip()
    if value.startswith('https://'):
        url = urlparse(value)
        if url.hostname not in {'miro.com', 'www.miro.com'}:
            raise AppError('Enter a miro.com board URL.')
        match = re.search(r'/board/([^/]+)', url.path)
        value = unquote(match.group(1)) if match else ''
    if not re.fullmatch(r'[a-zA-Z0-9_=\-]{5,120}', value):
        raise AppError('Enter a valid Miro board ID or URL.')
    return value

def plain(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', str(value)))).strip()

def chunk_source(source):
    words = source['text'].split()
    return [{'id': f"{source['id']}-{i}", 'sourceId': source['id'], 'content': ' '.join(words[i:i+200])}
            for i in range(0, len(words), 160)]

STOP = set('the a an of to in and is our what with for how are we on should from can this me'.split())
def tokens(text):
    return [t for t in re.findall('[a-z0-9]+', text.lower()) if t not in STOP]

def retrieve(query, chunks, count=6):
    query_tokens = tokens(query)
    scored = []
    for chunk in chunks:
        words = tokens(chunk['content'])
        score = sum(sum(w == t or w.startswith(t) for w in words) for t in query_tokens)
        if score:
            scored.append({**chunk, 'similarity': score / max(len(query_tokens), 1)})
    return sorted(scored, key=lambda c: -c['similarity'])[:count]

class Providers:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings, self.client = settings, client

    async def gemini(self, model, operation, body):
        if not re.fullmatch(r'[a-zA-Z0-9.\-]+', model):
            raise AppError('Invalid configured Gemini model.', 503)
        for attempt in range(2):
            try:
                response = await self.client.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:{operation}',
                    headers={'x-goog-api-key': self.settings.gemini_key}, json=body, timeout=45)
            except httpx.HTTPError:
                raise AppError('Gemini connection timed out. Please retry.', 503) from None
            if response.is_success:
                try:
                    value = response.json()
                except ValueError:
                    raise AppError('Gemini returned an invalid response.', 502) from None
                if not isinstance(value, dict):
                    raise AppError('Gemini returned an invalid response.', 502)
                return value
            if response.status_code in {429, 502, 503, 504}:
                if not attempt:
                    await asyncio.sleep(1.2)
                    continue
                raise AppError('Gemini rate limit reached.' if response.status_code == 429 else 'Gemini is temporarily busy.', 429 if response.status_code == 429 else 503)
            raise AppError(f'Gemini request failed ({response.status_code}). Check backend configuration and quota.', 502)

    async def embed(self, text, query=False):
        model = self.settings.embedding_model
        data = await self.gemini(model, 'embedContent', {'model': f'models/{model}', 'content': {'parts': [{'text': text}]},
            'taskType': 'RETRIEVAL_QUERY' if query else 'RETRIEVAL_DOCUMENT', 'outputDimensionality': 768})
        values = data.get('embedding', {}).get('values')
        if not isinstance(values, list) or len(values) != 768 or any(not isinstance(x, (float, int)) or not math.isfinite(x) for x in values):
            raise AppError('Embedding model must return 768 finite dimensions.', 502)
        return values

    async def generate(self, prompt, structured=False):
        body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': .2, 'maxOutputTokens': 4000, **({'responseMimeType': 'application/json'} if structured else {})}}
        try:
            data = await self.gemini(self.settings.gemini_model, 'generateContent', body)
        except AppError as error:
            if error.status != 503 or not self.settings.fallback_model:
                raise
            data = await self.gemini(self.settings.fallback_model, 'generateContent', body)
        candidates = data.get('candidates') if isinstance(data, dict) else None
        first = candidates[0] if isinstance(candidates, list) and candidates else None
        content = first.get('content') if isinstance(first, dict) else None
        parts = content.get('parts') if isinstance(content, dict) else None
        text = ''.join(p['text'] for p in parts if isinstance(p, dict) and isinstance(p.get('text'), str) and not p.get('thought')) if isinstance(parts, list) else ''
        if not text:
            raise AppError('Gemini returned no text. Please try a different question.', 502)
        return text

    async def miro(self, path, method='GET', body=None):
        if not self.settings.miro_token:
            raise AppError('Configure the Miro token in the backend.', 503)
        try:
            response = await self.client.request(method, f'https://api.miro.com/v2/{path}',
                headers={'Authorization': f'Bearer {self.settings.miro_token}'}, json=body, timeout=20)
        except httpx.HTTPError:
            # Never automatically repeat a write with an uncertain outcome.
            raise AppError('Miro connection failed. Inspect the board before retrying a publication.', 502) from None
        if not response.is_success:
            error = AppError(f'Miro request failed ({response.status_code}). Check board permissions and token.', 502)
            error.confirmed_rejection = 400 <= response.status_code < 500
            raise error
        try:
            value = response.json()
        except ValueError:
            raise AppError('Miro returned an invalid response. Inspect the board before retrying a publication.', 502) from None
        if not isinstance(value, dict):
            raise AppError('Miro returned an invalid response. Inspect the board before retrying a publication.', 502)
        return value
