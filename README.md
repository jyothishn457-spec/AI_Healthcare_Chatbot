# AI Healthcare Assistant Chatbot

An intelligent healthcare chatbot that answers user questions using uploaded medical
documents, FAQs and general healthcare knowledge through **Retrieval-Augmented
Generation (RAG)**.

- **Backend:** Python FastAPI
- **Frontend:** React.js (Vite) with a modern, responsive medical UI
- **AI Model:** OpenAI or Google Gemini (configurable via `.env`)
- **AI Framework:** LangChain
- **Vector Database:** ChromaDB (persistent)
- **Database:** SQLite (users + chat history)
- **Authentication:** JWT-based login with a default admin account

> **Medical disclaimer:** This project is for educational/demo purposes only. It is
> **not** a medical device and does **not** provide medical advice. Always consult a
> qualified healthcare professional.

---

## Features

### Chatbot
- Answer healthcare questions, explain diseases, medicines and preventive care
- Grounded answers using retrieved context from uploaded documents
- Always includes a "not a doctor" disclaimer and asks a follow-up question
- Detects emergency descriptions and advises calling emergency services

### RAG pipeline
- Loads **PDF**, **TXT** and **DOCX** medical files
- Splits documents into overlapping chunks
- Embeds chunks with OpenAI or Gemini embeddings
- Stores embeddings in a persistent ChromaDB collection
- Retrieves the most relevant chunks and feeds them to the LLM

### App
- Login / registration page with a clean medical design
- Dashboard with health assistant info and a chat button
- Chat interface: user messages on the right, AI on the left, typing animation,
  persisted chat history and a clear-chat option
- **Voice input**, **text-to-speech**, **dark mode**, **SOS emergency modal**
- **Admin document management panel** (upload / list / delete documents)
- API rate limiting, input validation, error handling and `.env`-hidden keys

---

## Project Structure

```
AI_Healthcare_Chatbot/
├── backend/
│   ├── main.py            # FastAPI app, routes, rate limiting
│   ├── chatbot.py         # LLM integration (OpenAI / Gemini)
│   ├── rag_pipeline.py    # load / split / embed / retrieve
│   ├── database.py        # SQLite layer (users, history, docs)
│   ├── auth.py            # PBKDF2 hashing + JWT tokens
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # routing, auth state, navbar, dark mode
│   │   ├── Login.jsx      # login / register
│   │   ├── Dashboard.jsx  # welcome + features
│   │   ├── Chat.jsx       # chat UI, voice, TTS, SOS, admin panel
│   │   ├── api.js         # axios client with JWT interceptor
│   │   └── styles.css
│   ├── package.json
│   └── README.md
├── data/
│   └── medical_documents/  # sample documents, auto-indexed on startup
└── README.md
```

---

## Installation

### Prerequisites
- Python **3.10+**
- Node.js **18+**
- An **OpenAI** API key or **Google Gemini** API key

### 1. Backend

```bash
cd backend

# create a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # macOS / Linux

# install dependencies
pip install -r requirements.txt

# configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
# then edit .env and add your OPENAI_API_KEY (or GEMINI_API_KEY)

# start the API
uvicorn main:app --reload --port 8000
```

The API is now live at `http://localhost:8000`. Interactive docs:
`http://localhost:8000/docs`.

On first start the backend:
1. Creates the SQLite database (`chatbot.db`)
2. Creates the default admin account (**admin / admin123**)
3. Indexes the sample documents from `data/medical_documents/` into ChromaDB

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. The Vite dev server proxies
`/api/*` requests to the FastAPI backend on port 8000, so no extra config is needed.

---

## Usage

1. **Log in** with `admin / admin123` (or register a new account).
2. **Add knowledge (admin):** click **Manage Documents** in the chat page, upload
   PDF / TXT / DOCX files, or simply drop them into `data/medical_documents/`
   and restart the backend.
3. **Chat:** type a question (e.g. *"What are the symptoms of diabetes?"*), use the
   **Voice** button to dictate, and press **Listen** on any AI answer to hear it.
4. Use the **SOS** button for emergency contact numbers, and the moon icon in the
   navbar to toggle dark mode.

### API overview

| Method | Endpoint             | Auth   | Description                        |
| ------ | -------------------- | ------ | ---------------------------------- |
| POST   | `/register`          | -      | Create an account                  |
| POST   | `/login`             | -      | Login, get a JWT                   |
| POST   | `/chat`              | Bearer | Ask a question (RAG)               |
| GET    | `/history`           | Bearer | Chat history                       |
| DELETE | `/history`           | Bearer | Clear chat history                 |
| POST   | `/upload`            | Admin  | Upload & index a document          |
| GET    | `/documents`         | Admin  | List indexed documents             |
| DELETE | `/documents/{id}`    | Admin  | Delete a document                  |
| GET    | `/health`            | -      | Health check                       |

Example chat request:

```json
POST /chat
Authorization: Bearer <token>
{
  "message": "What are the symptoms of diabetes?"
}
```

```json
{
  "response": "Common symptoms include increased thirst, frequent urination, ..."
}
```

---

## Configuration

Copy `backend/.env.example` to `backend/.env` and edit:

| Variable                  | Description                                  |
| ------------------------- | -------------------------------------------- |
| `LLM_PROVIDER`            | `openai` or `gemini`                         |
| `OPENAI_API_KEY`          | OpenAI key (when provider is `openai`)       |
| `OPENAI_MODEL`            | e.g. `gpt-4o-mini`                           |
| `GEMINI_API_KEY`          | Gemini key (when provider is `gemini`)       |
| `GEMINI_MODEL`            | e.g. `gemini-1.5-flash`                      |
| `DATABASE_URL`            | SQLite location                              |
| `CHROMA_DIR`              | ChromaDB persistence folder                  |
| `DATA_DIR`                | Folder auto-indexed on startup               |
| `SECRET_KEY`              | JWT signing secret (change it!)              |
| `DEFAULT_ADMIN_USERNAME`  | Auto-created admin username                  |
| `DEFAULT_ADMIN_PASSWORD`  | Auto-created admin password                  |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | RAG chunking parameters                |
| `RETRIEVAL_K`             | Number of chunks retrieved per query         |
| `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW` | Per-IP rate limits          |

**To switch providers** just set `LLM_PROVIDER=gemini` (or `openai`) and provide the
matching API key. Embeddings and the chat model both follow the provider.

---

## Deployment

### Backend on Render
1. Push the repo to GitHub.
2. On Render, create a new **Web Service** pointing at the repo.
3. Set the **Root Directory** to `backend`.
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add the environment variables from `.env.example` (no `.env` file on the server).

### Frontend on Vercel
1. On Vercel, import the repo and set the **Root Directory** to `frontend`.
2. Framework preset: **Vite** (build command `npm run build`, output `dist`).
3. Add an environment variable `VITE_API_URL` pointing to the deployed backend,
   e.g. `https://your-backend.onrender.com`.
4. In `frontend/src/api.js` the base URL falls back to `/api` when
   `VITE_API_URL` is not set — configure it to reach your backend.

---

## Sample Medical Documents

Ready-made documents for testing are in `data/medical_documents/`:

- `sample_common_conditions.txt` — diabetes, hypertension, asthma, flu, anemia
- `sample_medicines_guide.txt` — paracetamol, ibuprofen, metformin, amlodipine, amoxicillin
- `sample_preventive_care_faq.txt` — hydration, heart health, sleep, exercise, stress

These are indexed automatically the first time the backend starts.

---

## Troubleshooting

- **"OPENAI_API_KEY is not set"** — add your key to `backend/.env` and restart.
- **Voice button does nothing** — use Chrome or Edge; the Web Speech API is not
  available in every browser.
- **Port 8000 already in use** — run `uvicorn main:app --port 8001` and update the
  proxy target in `frontend/vite.config.js`.
- **chromadb install issues on Windows** — install with the standard wheels:
  `pip install chromadb==0.5.23` usually works on Python 3.10+; otherwise create a
  fresh virtual environment.

---

## Security Notes

- API keys are read from `.env` (never committed).
- Passwords are hashed with salted PBKDF2; sessions use signed JWTs.
- Inputs are validated with Pydantic and limited in length.
- Per-IP rate limiting protects `/login` and `/chat`.
- The CORS policy allows all origins for convenience — restrict it in production.

## License

MIT — free to use and modify for educational purposes.
