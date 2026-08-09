# HealthPilot AI — Medical Assistant

A full-stack, AI-powered medical assistant / patient portal (capstone project).

- **Backend:** Python FastAPI with SQLite (swappable to Postgres), JWT auth with
  hashed passwords, refresh-token rotation, per-user medical records.
- **Frontend:** React (Vite) with a clean clinical-but-friendly responsive UI,
  protected routes, sidebar navigation and dark mode.
- **AI:** RAG chatbot (OpenAI / Gemini via env var) + a deterministic symptom
  predictor that is always flagged "informational, not diagnostic".
- **Deployment:** `render.yaml` Blueprint for both services.

> **Medical disclaimer:** This project is for educational/demo purposes only. It
> is **not** a medical device and does **not** provide medical advice, diagnosis
> or treatment. Always consult a qualified healthcare professional.

---

## Live Demo

| Service  | URL                                                        |
| -------- | ---------------------------------------------------------- |
| Frontend | https://ai-healthcare-frontend-9x04.onrender.com            |
| Backend  | https://ai-healthcare-backend-jxmh.onrender.com            |
| API docs | https://ai-healthcare-backend-jxmh.onrender.com/docs       |

Log in with `admin` / `admin123`.

---

## Features

### Authentication & account
- Register, login, logout and **session refresh** (short-lived access tokens +
  revocable refresh tokens that rotate on every refresh).
- Passwords hashed with salted PBKDF2 — never logged or returned.
- Profile editing, notification preferences, change password and **account
  deletion** (password-confirmed).

### AI Doctor Chat
- RAG-powered answers grounded in your uploaded medical documents.
- Persistent **disclaimer banner** and an embedded "not a doctor" system prompt.
- **Named conversations**: start a new chat or continue an old one; history is
  stored per user. Sources are cited under each answer.
- Voice input, text-to-speech, chat export to PDF, emergency (SOS) resources.

### Symptom Prediction
- **Structured symptom checklist** (categorized, not free text) plus age / sex /
  duration context.
- Returns a **ranked list of possible conditions** with High / Moderate / Low
  confidence labels, plain-language explanations and next-step guidance.
- Red-flag detection (e.g. chest pain, breathing trouble) triggers urgent-care
  advice. Every result is flagged **informational, not diagnostic**.
- Full prediction history is saved per user.

### Appointments
- Book with doctor/specialty selection and a date/time picker.
- Status workflow: **pending → confirmed → completed**, plus **cancelled**.
- Filterable list, reschedule and cancel actions, confirmation state.

### Medical History & Prescriptions
- Timeline-style medical history and prescription records.
- Add / edit / delete, strictly scoped to the logged-in user **server-side**.

### Dashboard
- Quick-stat cards (Upcoming, Pending, Completed, Active prescriptions).
- Upcoming appointments + recent prescriptions lists with friendly empty states.
- Primary CTAs: AI Doctor, Predict Symptoms, Book Appointment.

---

## Project Structure

```
AI_Healthcare_Chatbot/
├── backend/
│   ├── main.py            # FastAPI app: lifespan, CORS, router wiring
│   ├── database.py        # SQLite layer (users, sessions, records, …)
│   ├── auth.py            # PBKDF2 hashing, JWT access + refresh tokens
│   ├── chatbot.py         # RAG LLM integration (OpenAI / Gemini)
│   ├── rag_pipeline.py    # load / split / embed / retrieve (ChromaDB)
│   ├── prediction.py      # symptom -> condition knowledge base + ranking
│   ├── ratelimit.py       # per-IP sliding-window rate limiting
│   ├── routers/
│   │   ├── auth.py        # register / login / refresh / logout
│   │   ├── chat.py        # /chat + conversation sessions
│   │   ├── appointments.py
│   │   ├── records.py     # medical history + prescriptions
│   │   ├── profile.py     # profile, settings, account deletion
│   │   ├── prediction.py  # symptom checklist + prediction history
│   │   └── documents.py   # admin document upload/delete
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # routing, auth guard, dark mode, shell
│   │   ├── api.js             # axios + JWT refresh interceptor
│   │   ├── utils.js           # date / status helpers
│   │   ├── components/        # Sidebar, StatCard, DisclaimerBanner, …
│   │   └── pages/             # Login, Dashboard, Chat, Predict, …
│   ├── .env.production        # VITE_API_URL for production builds
│   └── package.json
├── data/
│   └── medical_documents/     # sample documents, auto-indexed on startup
├── render.yaml                # Render Blueprint: backend + frontend
├── START_SERVERS.bat          # one-click local launcher
└── README.md
```

---

## Installation

### Prerequisites
- Python **3.10+**
- Node.js **18+**
- An **OpenAI** or **Google Gemini** API key

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # macOS / Linux

pip install -r requirements.txt

copy .env.example .env         # then add your OPENAI_API_KEY or GEMINI_API_KEY
uvicorn main:app --reload --port 8000
```

The API is live at `http://localhost:8000` — interactive docs:
`http://localhost:8000/docs`.

On first start the backend:
1. Creates the SQLite database (and migrates any existing one)
2. Creates the default admin account (**admin / admin123**)
3. Indexes sample documents from `data/medical_documents/` into ChromaDB

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` to the
backend on port 8000.

---

## API Overview

| Method   | Endpoint                 | Auth  | Description                                    |
| -------- | ------------------------ | ----- | ---------------------------------------------- |
| POST     | `/register`              | -     | Create an account (returns tokens)             |
| POST     | `/login`                 | -     | Login, get access + refresh tokens             |
| POST     | `/refresh`               | -     | Rotate a refresh token                         |
| POST     | `/logout`                | Bearer | Revoke refresh tokens                         |
| POST     | `/chat`                  | Bearer | Ask the AI Doctor (creates/continues session)  |
| GET/POST | `/chat/sessions`         | Bearer | List / create conversations                    |
| GET/PATCH/DELETE | `/chat/sessions/{id}` | Bearer | Read / rename / delete a conversation   |
| POST     | `/predict`               | Bearer | Score symptom checklist → ranked conditions    |
| GET      | `/predict/symptoms`      | Bearer | Symptom checklist catalogue                    |
| GET      | `/predict/history`       | Bearer | Past prediction runs                           |
| GET/POST | `/appointments`          | Bearer | List / book appointments                       |
| PATCH/DELETE | `/appointments/{id}` | Bearer | Reschedule / cancel                       |
| GET      | `/appointments/doctors`  | -     | Doctor/specialty catalogue                     |
| GET/POST | `/records/history`       | Bearer | Medical history CRUD                           |
| PATCH/DELETE | `/records/history/{id}` | Bearer | Edit / delete history entry              |
| GET/POST | `/records/prescriptions` | Bearer | Prescriptions CRUD                             |
| PATCH/DELETE | `/records/prescriptions/{id}` | Bearer | Edit / delete prescription         |
| GET/PATCH | `/profile`              | Bearer | Read / update profile & preferences            |
| DELETE   | `/profile`               | Bearer | Delete account (password-confirmed)            |
| POST     | `/upload`                | Admin  | Upload & index a medical document              |
| GET/DELETE | `/documents[/{id}]`   | Admin  | Manage indexed documents                       |
| GET      | `/health`                | -     | Health check                                   |

---

## Configuration

Copy `backend/.env.example` to `backend/.env` and edit:

| Variable                  | Description                                  |
| ------------------------- | -------------------------------------------- |
| `LLM_PROVIDER`            | `openai` or `gemini`                         |
| `OPENAI_API_KEY`          | OpenAI key (when provider is `openai`)       |
| `OPENAI_MODEL`            | e.g. `gpt-4o-mini`                           |
| `GEMINI_API_KEY`          | Gemini key (when provider is `gemini`)       |
| `GEMINI_MODEL`            | e.g. `gemini-3.5-flash`                       |
| `DATABASE_URL`            | SQLite location (swap to Postgres in prod)   |
| `CHROMA_DIR`              | ChromaDB persistence folder                  |
| `DATA_DIR`                | Folder auto-indexed on startup               |
| `SECRET_KEY`              | JWT signing secret (change it!)              |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default 60)       |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | Refresh token lifetime (default 7)      |
| `DEFAULT_ADMIN_USERNAME`  | Auto-created admin username                  |
| `DEFAULT_ADMIN_PASSWORD`  | Auto-created admin password                  |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | RAG chunking parameters                |
| `RETRIEVAL_K`             | Number of chunks retrieved per query         |
| `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW` | Per-IP rate limits          |

**To switch AI providers** set `LLM_PROVIDER=gemini` (or `openai`) and provide
the matching API key. The symptom predictor is deterministic and runs fully
offline — it needs no API key.

---

## Deployment

Both services are defined in a single `render.yaml` **Blueprint** at the repo
root and deploy automatically on every push to `main`.

### Services

1. **ai-healthcare-backend** — web service, `runtime: python`, `rootDir: backend`,
   free plan, `uvicorn main:app` on `$PORT`, health check at `/health`.
   - Pinned `PYTHON_VERSION: 3.12.11` — required because Render's default (3.14)
     has no prebuilt wheels for the pinned Rust-based deps.
2. **ai-healthcare-frontend** — static site, `runtime: static`, `rootDir: frontend`,
   `npm install && npm run build`, publishes `./dist`.
   - `VITE_API_URL` is set to the deployed backend and baked into the bundle at
     build time (also mirrored in `frontend/.env.production`).

### Deploying (one-time setup)

1. Push the repo to GitHub.
2. On Render: **New + → Blueprint → connect this GitHub repo**.
3. Render reads `render.yaml`, creates both services, and prompts for the secrets
   marked `sync: false` (`GEMINI_API_KEY`, `OPENAI_API_KEY`) — paste your keys.
4. Hit **Apply**. After the first deploy, copy each service's `.onrender.com` URL.
5. Re-sync the Blueprint (`Sync Blueprint`) after any change to `render.yaml`.

**Free-tier note:** SQLite, ChromaDB and uploaded documents live in ephemeral
storage and reset on restart/redeploy. Sample documents are re-indexed
automatically on first start.

---

## Sample Medical Documents

Ready-made documents for testing are in `data/medical_documents/`:
- `sample_common_conditions.txt` — diabetes, hypertension, asthma, flu, anemia
- `sample_medicines_guide.txt` — paracetamol, ibuprofen, metformin, amlodipine
- `sample_preventive_care_faq.txt` — hydration, heart health, sleep, stress

These are indexed automatically the first time the backend starts.

---

## Security Notes

- API keys are read from `.env` (never committed).
- Passwords are hashed with salted PBKDF2; access tokens are short-lived JWTs;
  refresh tokens are random, stored hashed, rotated on refresh and revoked on
  logout.
- All personal data endpoints are scoped to the authenticated user server-side.
- Inputs are validated with Pydantic and length-limited.
- Per-IP rate limiting protects `/login` and `/chat`.
- CORS currently allows all origins for convenience — restrict it in production.

## License

MIT — free to use and modify for educational purposes.
