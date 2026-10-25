# FastAPI migration verification

Verified locally on Windows, 25 October 2026. Two requested agents reviewed the frontend and backend; their blocking findings were fixed and reviewed again. This is evidence for the tested paths, not a guarantee that every production scenario is defect-free.

| Check | Result |
| --- | --- |
| FastAPI unit/integration suite | 12 passed |
| Frontend browser regression suite | Passed: file form submission, auth cleanup, workspace isolation, stale response ordering, chat navigation, unsaved roadmap tabs, transport errors |
| Combined Next.js → FastAPI browser workflow | Passed: real PDF/DOCX extraction, saved scoped chats/citations, analysis freshness, comments/tasks, owners/dates, approval gate, auto-sync timer, desktop/mobile layout |
| Supabase RLS regression SQL | Passed in rolled-back transaction: invite acceptance/revocation, outsider isolation, shared retrieval, stale revisions, editor deletion denial, membership removal |
| Real RP-1 board read | 57 items extracted; 6 chunks embedded with real Gemini credentials |
| Real Supabase semantic retrieval | 6 indexed board chunks returned by existing pgvector RPC under authenticated RLS; minimum cosine similarity 0.663 for the test query |
| Real Gemini answer | Answer generated from retrieved excerpts; all numeric citations validated and grouped markers normalized into individually clickable references |
| Miro publication recovery | Mocked tests passed: sticky notes/connectors, HTML escaping, CAS retry, persisted journal restart, no duplicate acknowledged writes, uncertain outcome blocks automatic repeat |
| Live security smoke | Passed: auth required, anonymous database reads denied, private keys absent from public config, sign-in renders without browser exceptions |
| Private key boundary | Passed: no configured Gemini/Miro secrets in scanned frontend source/build artifacts; frontend env contains backend address only |
| Retrieval benchmark | 4/4 local cases, Recall@3 1.0; keyword-only benchmark, separate from live semantic diagnostic |
| TypeScript / production build | Passed |
| Local production process smoke | Standalone Next.js rendered with static assets; API proxy/auth gate worked; FastAPI production health passed and docs disabled |
| Docker Compose configuration | Validated; Docker daemon unavailable, so container image build/runtime not executed |
| Raspberry Pi / ARM runtime | Not executed: no reachable device or SSH destination supplied |
| Remote GitHub CI / deployment | Workflow prepared; no remote run or deployment performed |

The real board was read without changing it. Live publication was not exercised; Miro write tests used mocks. Existing workspace data and credentials were preserved. API keys were relocated, not rotated.

Deployment requires the documented single backend worker/replica, private persistent publication journals, correct HTTPS origin/auth configuration, and host secret injection. See README.md for commands and limits. The ignored local `.data/live-rag-report.json` contains the detailed board diagnostic, including the answer.
