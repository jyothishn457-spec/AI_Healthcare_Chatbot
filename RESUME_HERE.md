# Session Progress — save point

Last updated: Aug 08 2026. Backend is DEPLOYED and LIVE. Two things remain: verify frontend deploy, and walk through cleanup/next steps.

## Status

- Backend live at **https://ai-healthcare-backend-jxmh.onrender.com** (auto-deploy on, `main` branch).
- Frontend = separate Render **Static Site** (created via dashboard, NOT in render.yaml). Backend only service is defined in `render.yaml`.

## What was fixed this session (all committed & pushed to `main`)

1. `64cf385` — render.yaml: use current blueprint fields (`autoDeployTrigger: commit`, `healthCheckPath: /health`).
2. `c570a1d` — **Fixed Render build failure.** Root cause: Render defaults to Python 3.14, which has no prebuilt wheels for our 2024-era Rust-based deps (`onnxruntime`, `pydantic-core`, `tokenizers`, `tiktoken`) -> pip builds from source -> needs Cargo -> `Read-only file system` on `/usr/local/cargo/...`. Fix: added `PYTHON_VERSION: "3.12.11"` env var to render.yaml. All deps now install from wheels.
3. `250562c` — Frontend now points at the live backend. Added `frontend/.env.production`:
   - `VITE_API_URL=https://ai-healthcare-backend-jxmh.onrender.com`
   - No `/api` prefix — backend routes are at root (see backend/main.py: `/login`, `/chat`, `/history`, `/upload`, etc.).
   - CORS is already permissive (`allow_origins=["*"]` in main.py), no backend change needed.
   - In dev, `src/api.js` falls back to `/api` (Vite proxy in `vite.config.js` -> localhost:8000).

## PENDING (next session)

1. **Frontend redeploy / verify** — push `250562c` should have auto-triggered the static site rebuild (auto-deploy on, connected to this repo). Vite loads `.env.production` automatically on `npm run build`, so no dashboard env var needed.
   - Check Render dashboard -> frontend static site -> Deploys -> last deploy built from `250562c`.
2. **Verify E2E** once frontend is live (frontend URL not yet known — user was going to paste it):
   - Open frontend, log in with `admin` / `admin123` (auto-created; see render.yaml DEFAULT_ADMIN_*).
   - Send a chat message; confirm AI answers.
   - Confirm no CORS errors in browser console.
3. **Known Render free-tier limitations to remember:** ChromaDB, SQLite, and uploaded docs live in ephemeral storage — reset on every restart/redeploy. Sample docs in `data/medical_documents` are re-indexed on first start (DATA_DIR env).
4. **No secrets committed.** GEMINI_API_KEY and OPENAI_API_KEY are `sync: false` in render.yaml — must be filled in the Render dashboard.

## Local quick-start (already built in)

- `start_app.bat` at repo root launches backend + frontend locally. Local dev backend runs on port 8000, frontend on 5173.
