# Miro × Gemini Workspace

## Platform
Web, responsive desktop and mobile.

## Stack
User requested Next.js, TypeScript, Tailwind CSS, Node.js, Supabase PostgreSQL and pgvector.

## Product Purpose
Import Miro brainstorming boards and research documents, retrieve relevant knowledge, generate cited Gemini answers, and review a visual project plan before publishing changes to Miro.

## Users
Assumption: research and product teams managing brainstorming and project planning.

## Capabilities and Constraints
User confirmed all three main surfaces: research overview, AI chat with source inspection, visual roadmap editor. Authentication, incremental synchronization, secure server integrations and retrieval evaluation are required. Live integrations require user-owned credentials. Local demo must clearly identify sample data and deterministic retrieval.

## Brand Commitments
User requested a retro visual refresh with glows and gradients, and explicitly selected dark espresso with warm sunset glow. Preserve all connected-service workflows and explicit approval before Miro publishing.

## Collaboration and Research Features
User requested automatic sync, saved chats, PDF/Word ingestion, grounded themes/gaps/conflicts, shared workspaces with comments and tasks, and connected Miro plans with owners and deadlines. Automatic sync runs while the tab is open and visible. Team access uses expiring revocable invite codes and editor membership. Existing live research must be preserved; test and preview data is isolated.


## FastAPI service migration
Provider credentials now live only in backend/.env. The Next.js frontend proxies the existing /api contract to private FastAPI, preserving verified Supabase JWT/RLS, scoped pgvector retrieval and explicit Miro publication approval. Miro access fails closed through user/board allowlists. Single-worker durable publication journals prevent blind retries after uncertain writes. See README.md for verified tests, deployment and remaining platform limits.
