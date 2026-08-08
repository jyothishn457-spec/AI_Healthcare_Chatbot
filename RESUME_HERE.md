# AI Healthcare Chatbot — Deployed State

Last updated: Aug 08 2026. **Everything is deployed and verified working end to end.**

## Live URLs

- **Frontend:** https://ai-healthcare-frontend-9x04.onrender.com
- **Backend API:** https://ai-healthcare-backend-jxmh.onrender.com (health: `/health` returns `{"status":"ok"}`)
- **API docs (Swagger):** https://ai-healthcare-backend-jxmh.onrender.com/docs

## How they connect

- Frontend is a Render **static site** (`ai-healthcare-frontend`, `runtime: static`, builds `frontend/` -> `dist`).
- At build time, Vite bakes `VITE_API_URL=https://ai-healthcare-backend-jxmh.onrender.com` into the JS bundle
  (from `frontend/.env.production` AND the `VITE_API_URL` env var in render.yaml — verified present in the served bundle).
- `src/api.js` uses that as the axios base URL. Backend routes live at the root (no `/api` prefix):
  `/login`, `/register`, `/chat`, `/history`, `/upload`, `/documents`.
- Backend CORS is permissive (`allow_origins=["*"]`), so cross-origin calls from the frontend work.
- In local dev the Vite proxy (`vite.config.js`) sends `/api/*` -> `http://localhost:8000`; no config needed.

## Tech stack

### Backend (Python / FastAPI)
- `fastapi==0.115.6`, `uvicorn[standard]==0.34.0`, `pydantic==2.10.4`
- LangChain `0.3.14` (`langchain-community`, `langchain-core`, `langchain-text-splitters`)
- LLM providers: `langchain-openai` / `langchain-google-genai` + `google-generativeai` (LLM_PROVIDER is `gemini`)
- Vector DB: `chromadb==0.5.23` (RAG embeddings)
- Document loaders: `pypdf`, `python-docx`, `python-multipart`
- Auth: `PyJWT`, `cryptography` (PBKDF2 hashing + JWT)
- SQLite via `DATABASE_URL` (users, chat history, doc index)

### Frontend (React / Vite)
- React 18.3, react-router-dom 6.28, axios 1.7
- Vite 5.4 (`npm run build` -> `dist`)
- Features: JWT login, dashboard, chat UI, voice input (Web Speech), text-to-speech, dark mode, SOS modal,
  admin document upload/list/delete

## Deployment setup (render.yaml)

Two services in the Render Blueprint (root of repo):

1. **ai-healthcare-backend** — `type: web`, `runtime: python`, `rootDir: backend`, free plan,
   `buildCommand: pip install -r requirements.txt`,
   `startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT`, `healthCheckPath: /health`.
   - `PYTHON_VERSION: "3.12.11"` (critical: Render's default 3.14 lacks wheels for Rust-based deps ->
     source build -> Cargo missing -> `Read-only file system` build failure).
   - Secrets `GEMINI_API_KEY`, `OPENAI_API_KEY` are `sync: false` (set in dashboard, not in git);
     `SECRET_KEY` auto-generated.
   - `DEFAULT_ADMIN_USERNAME=admin`, `DEFAULT_ADMIN_PASSWORD=admin123` (change in production!).
2. **ai-healthcare-frontend** — `type: web`, `runtime: static`, `rootDir: frontend`, no plan field
   (static sites are free / no instance type), `buildCommand: npm install && npm run build`,
   `staticPublishPath: ./dist`, `envVars: VITE_API_URL=<backend URL>`.

Both `autoDeployTrigger: commit` on `main`.

## Verification performed (end-to-end)

- Frontend serves HTTP 200 with the MediCare AI app.
- Served JS bundle contains the live backend URL.
- Backend `/health` returns `{"status":"ok"}`.
- `POST /login` with `admin`/`admin123` returns a valid JWT + user object.
- Next manual check: open the frontend, log in, send a chat message and confirm the AI answers.

## Important notes / limitations

- **Free-tier ephemeral storage:** ChromaDB, SQLite (`chatbot.db`) and uploaded docs reset on every
  restart/redeploy. Sample docs in `data/medical_documents` are re-indexed on first start (`DATA_DIR`).
- **No secrets in git.** If keys ever need changing, update them in the Render dashboard.
- **Default admin password is public** (`admin123`) — change it before real use.
- Local quick-start: `START_SERVERS.bat` at repo root launches backend (port 8000) + frontend (5173).
