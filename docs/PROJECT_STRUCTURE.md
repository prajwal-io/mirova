# Project structure

```text
mirova/
├── app/                       Next.js routes, page, layout, and global styles
├── components/                Reusable React interface components
├── lib/                       Shared frontend types and demo/evaluation data helpers
├── backend/
│   ├── app/                   FastAPI entry point, routes, services, and providers
│   ├── scripts/               Backend diagnostics and maintenance commands
│   ├── tests/                 FastAPI tests and document fixtures
│   ├── .env.example           Backend configuration template (no real secrets)
│   └── requirements-lock.txt  Pinned Python dependencies
├── supabase/
│   ├── schema.sql             Base database schema
│   ├── collaboration.sql      Workspace and collaboration schema
│   └── tests/                 Database policy checks
├── tests/
│   ├── e2e/                   Browser and full-workflow checks
│   └── evaluation/            Local retrieval evaluation
├── scripts/
│   ├── checks/                Integration and security diagnostics
│   ├── ui/                    Capture and visual-review utilities
│   └── dev.mjs                Combined frontend/backend launcher
├── docs/                      Product, design, test, and structure documents
├── .github/workflows/          Continuous integration configuration
├── README.md                   Project overview and run instructions
├── DESIGN.md                   Frontend design reference
├── AGENTS.md                   Repository instructions for coding agents
└── package.json                Frontend commands and dependencies
```

Put new React pages in `app/`, reusable UI in `components/`, shared frontend types in `lib/`, and API or provider logic in `backend/app/`. Keep tests beside the system they exercise: Python API tests in `backend/tests/`, browser tests in `tests/e2e/`, retrieval checks in `tests/evaluation/`, and database policy checks in `supabase/tests/`. Put operational utilities in `scripts/checks/` or `scripts/ui/`; keep only the combined launcher at the top of `scripts/`.
