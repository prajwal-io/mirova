# Mirova — Next.js + FastAPI research workspace

Open http://localhost:3000 for the authenticated app, or http://localhost:3001 for the isolated local demo. The Next.js frontend proxies `/api/*` to a private FastAPI service. Browsers use one application origin; Gemini/Miro calls, extraction, embeddings, retrieval, shared workspace changes, and publishing run in Python.

## Local setup

Requirements: Node.js 24, Python 3.12, and the existing Supabase schema.

```powershell
npm ci
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements-lock.txt
```

Copy `.env.example` to `.env.local` and `backend/.env.example` to `backend/.env` on a fresh checkout. This installation has already moved the configured credentials to `backend/.env`. The frontend file contains only `BACKEND_URL`. Do not copy private credentials into frontend environment variables, source, Docker build arguments, or GitHub. Both real environment files are ignored by Git.

On Linux/macOS use `python3 -m venv backend/.venv` and `backend/.venv/bin/python` for the Python commands below. `npm run dev` automatically selects the virtual environment executable on either OS.

```powershell
npm run dev
# One launcher starts Next.js :3000 and FastAPI :8000 on loopback.
npm run dev:demo
# Separate disposable preview: Next.js :3001 and FastAPI :8001.
```

FastAPI development docs: http://localhost:3000/api/docs. Documentation endpoints are disabled with `APP_ENV=production`. Use Ctrl+C to stop a foreground launcher. Health: `/api/health`.

For a new Supabase project apply `supabase/schema.sql` then `supabase/collaboration.sql`. The connected project already has both and the atomic source update function. Every backend database request uses the verified caller JWT and publishable key, retaining RLS; no service-role key is used. The Supabase URL and publishable key are deliberately returned by `/api/config` for browser authentication. They are public configuration. Gemini, Miro access token and Miro client secret are never returned.

## Miro permissions and publishing

`MIRO_ALLOWED_USER_IDS` and `MIRO_ALLOWED_BOARD_IDS` are comma-separated explicit allowlists, empty by default. The existing owner and RP-1 board have been enabled in this installation. An arbitrary new app account cannot use the shared organization token. Add only authorized account UUIDs/board IDs to the backend environment. Per-user Miro OAuth is not implemented; the client secret is reserved for it.

Import reads paginated board text (5,000 items / 200,000 characters maximum), preserves source URLs and hashes, chunks 200 words with 40-word overlap, and creates 768-dimensional Gemini embeddings. Supabase pgvector retrieves permission-scoped evidence before Gemini answers. Unknown selected sources and invalid model citation numbers are rejected. All AI-derived plans require explicit approval before any Miro write. Publishing creates owner/deadline sticky notes and connected arrows; chat and sync do not publish changes.

Publication IDs are fsynced into a private durable journal before metadata merge/retry, preserving acknowledged items across CAS conflicts and restarts. A network failure or crash with an unknown remote outcome blocks automatic retry. Inspect the Miro board and reconcile the private journal before resuming; never delete an uncertain journal to force a blind retry. Confirmed rejected writes can be retried. Published plans are immutable; create a new draft for revisions.

This implementation supports **one backend worker and one replica with persistent `.data` storage**. Do not horizontally scale it without a distributed publication lease/journal and rate limiter. The supplied Compose configuration enforces one worker/replica and mounts a persistent volume. Back up that private volume. Rate limits are by verified user with an additional IP limit; the public edge should enforce independent request/auth limits.

## Features and limits

- Miro automatic checks every 1/5/15 minutes while the visible workspace is open, with overdue checks on return. Hashing skips unchanged embeddings. Team data refreshes every 30 seconds. Browser-closed scheduling/webhooks remain an extension.
- Saved shared chats, selected sources, history and clickable citation excerpts; 50 conversations / 100 messages each.
- PDF, DOCX, TXT, Markdown and CSV uploads: 10 MB / 200 PDF pages / 200,000 extracted characters. Extraction runs in a separate terminable process with a 30-second timeout and one extraction slot; Linux adds 512 MB and CPU limits, and PDF/DOCX expansion is bounded. Scanned PDFs need prior OCR; save old `.doc` as `.docx`. Only extracted text is retained. This is not an antivirus service.
- Source-grounded themes, proposed gaps and possible conflicts across up to 30 source excerpts. Conflicts need at least two valid source IDs. Stale analysis is marked. Graph shows up to 10 sources; all remain available in the library.
- Shared workspaces via revocable seven-day invite codes; owner/editor access, comments, owners/deadlines and task completion. No invitation emails are sent. Treat invite codes as credentials.
- Roadmap edits and unsaved drafts persist across plan tabs. Provider requests have bounded timeouts; account/workspace changes cancel obsolete frontend requests and clear private UI state.

## Tests

```powershell
backend/.venv/Scripts/python -m pytest backend/tests -q
npm run typecheck
npm run eval
npm run test:frontend
npm run test:workflow
node --env-file=backend/.env scripts/live-smoke.mjs
backend/.venv/Scripts/python scripts/check-secret-boundary.py
npm run build
```

`test:frontend` uses browser API/auth mocks against running :3000. It covers actual upload form validity, stale response isolation, sign-out cleanup, chat navigation, draft retention and transport errors. `test:workflow` needs the isolated preview running; it resets only `.data/preview` and covers real HTTP PDF/DOCX imports, saved chat/citations, analysis staleness, comments/tasks, approval, owners/dates, automatic sync and desktop/mobile layouts. PDF/DOCX fixtures are in `backend/tests/fixtures`.

Python tests cover API workflows, auth/JWT forwarding, membership denial, CAS conflicts, provider errors, model/citation validation, archive limits, parser subprocesses, Miro allowlists/pagination/incremental indexing, publication recovery/uncertainty, and workspace concurrency. Miro write tests use mocks. `scripts/test-team-policies.sql` runs real Supabase invite/isolation/retrieval/revocation tests inside a rolled-back transaction.

`python -m backend.live_diagnostic` explicitly reads the configured real board and generates fresh embeddings/query vector without changing it. It writes an ignored diagnostic SQL query for the existing pgvector RPC. Run that query through authorized Supabase tooling, save the returned rows as `.data/live-rag-retrieved.json`, then run `python -m backend.live_diagnostic --answer`. The completed local report is `.data/live-rag-report.json`. This diagnostic was performed against RP-1 and the real Gemini/Supabase services; its SQL step uses an authenticated RLS context in a rolled-back transaction, not a browser login. It does not test a real Miro write.

## Deployment

Set `ALLOWED_ORIGINS` to the actual HTTPS application origin in `backend/.env`, configure Supabase Auth site/redirect URLs, and run:

```powershell
docker compose config --quiet
docker compose up --build -d
```

Only frontend port 3000 is published; backend port 8000 stays on the private Compose network. Put an HTTPS reverse proxy in front of port 3000. Never expose FastAPI directly to the public network. The backend runs as a non-root user with a private persistent journal volume, one worker/replica, and memory/CPU limits. Container builds exclude credentials and local data. Inject production secrets using the hosting platform’s secret manager instead of committing an environment file.

`npm run build` plus `npm start` can also run both services on one host; the production launcher requires `APP_MODE=live`. Standalone Docker frontend artifacts are produced by Next.js.

The GitHub Actions workflow runs Python, build, retrieval and browser regression tests against an isolated demo without production credentials. It has been prepared locally; a remote CI run has not occurred.

Local production builds and server smoke tests are verified. Docker configuration is validated; the Docker daemon was unavailable during this run, so container builds/runtime are not certified. No reachable Raspberry Pi was supplied, so actual Pi/ARM runtime tests have not been run. The Dockerfiles use multi-architecture base images; validate dependency installation and resource limits on the target device before deployment. No remote deployment has been performed.
