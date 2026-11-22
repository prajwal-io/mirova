# Mirova

Mirova is a simple RAG project built with Miro and Gemini. It helps teams turn board ideas and research into cited answers and project plans.

## What does it do?

Mirova imports text from Miro boards and research documents, indexes it, then retrieves relevant passages to ground Gemini’s answers. Teams can explore findings, discuss them, and prepare plans for review.

## Main features

- Import and sync text from authorized Miro boards.
- Upload PDF, DOCX, TXT, Markdown, and CSV files.
- Ask questions and inspect clickable source citations.
- Explore research themes, gaps, and possible conflicts.
- Save chats and collaborate through shared workspaces, comments, and tasks.
- Draft roadmaps with owners and deadlines; approve them before publishing sticky notes and connectors to Miro.

## Tech stack

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, custom CSS.
- **Backend:** Python 3.12, FastAPI, Uvicorn.
- **AI:** Gemini for answers and embeddings.
- **Data and authentication:** Supabase Auth, PostgreSQL, pgvector.
- **Integrations and documents:** Miro REST API, pypdf, defusedxml.

## Architecture

Next.js serves the interface and proxies `/api` requests to FastAPI. Supabase Auth signs users in; FastAPI verifies their token and accesses workspace data under Supabase’s row-level security policies.

```mermaid
flowchart LR
    U[User browser] -->|Workspace UI| N[Next.js frontend]
    U -->|Sign in| A[Supabase Auth]
    N -->|/api proxy| F[FastAPI backend]
    F -->|User token and row-level security| D[(Supabase PostgreSQL and pgvector)]
    F -->|Embeddings and cited answers| G[Gemini API]
    F -->|Read boards and publish approved plans| M[Miro API]
```

## Use cases

Mirova is useful when teams need to connect visual brainstorming with research and move from evidence to action. For example, teams can:

- Summarize a workshop or meeting.
- Find themes and unanswered questions across research.
- Answer product discovery questions with source citations.
- Coordinate work with shared comments, tasks, owners, and deadlines.
- Publish an approved roadmap to a Miro board.

## How to run it

You need Node.js 24 and Python 3.12.

1. Install dependencies:

   ```powershell
   npm ci
   python -m venv backend/.venv
   backend/.venv/Scripts/python -m pip install -r backend/requirements-lock.txt
   ```

2. Copy `.env.example` to `.env.local` and `backend/.env.example` to `backend/.env`. Configure Supabase, Gemini, and Miro in `backend/.env`; keep provider secrets out of frontend configuration.

3. For a new Supabase project, apply `supabase/schema.sql` and `supabase/collaboration.sql`. Set the authorized Miro user and board allowlists in `backend/.env`.

4. Start the app:

   ```powershell
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000). For the isolated demo, run `npm run dev:demo` and open [http://localhost:3001](http://localhost:3001).

## Production deployment (Vercel)

Deploy this repository as two Vercel projects: the frontend uses the repository root; the FastAPI project uses `backend/` as its root directory. The backend entrypoint and runtime dependencies are configured in `backend/pyproject.toml`, `backend/requirements.txt`, and `backend/.python-version`.

1. Deploy the backend project first and copy its stable HTTPS deployment URL.
2. Add these server-only variables to the backend Vercel project for Production and Preview: `APP_MODE=live`, `APP_ENV=production`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `GEMINI_API_KEY`, `MIRO_ACCESS_TOKEN`, `MIRO_ALLOWED_USER_IDS`, `MIRO_ALLOWED_BOARD_IDS`, and `ALLOWED_ORIGINS`. Set `ALLOWED_ORIGINS` to the exact frontend HTTPS origin(s). Do not add provider secrets to the frontend project.
3. Set frontend project variable `BACKEND_URL` to the deployed backend HTTPS URL, then redeploy the frontend. The Next.js rewrite proxies `/api/*` to FastAPI.
4. In the Vercel Firewall, configure an IP-based rate-limit rule for `/api/*` (at least 600 requests per IP per minute). The backend enforces the additional shared per-user limit through Supabase.
5. In Supabase Auth settings, enable leaked-password protection, configure the frontend production URL and redirect URLs, and configure custom SMTP before enabling public email sign-up.
6. Verify `/api/health`, sign-in, workspace isolation, Miro read access, and an approved test publication on the deployed HTTPS URL before inviting users.

The backend stores publication recovery journals in the user's Supabase workspace record with compare-and-swap writes, so concurrent Vercel instances cannot blindly publish the same plan twice. Uncertain Miro write outcomes remain blocked for manual reconciliation.

For self-hosting, use the existing Docker Compose setup. Its backend must remain a single replica unless the deployment uses the same shared Supabase coordination configured for Vercel.
