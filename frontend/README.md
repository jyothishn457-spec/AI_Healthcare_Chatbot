# MediCare AI - Frontend

React (Vite) frontend for the AI Healthcare Assistant chatbot.

## Setup

```bash
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to the FastAPI
backend on `http://localhost:8000` (see `vite.config.js`).

## Scripts

| Command           | Description                        |
| ----------------- | ---------------------------------- |
| `npm run dev`     | Start the dev server               |
| `npm run build`   | Build a production bundle to `dist` |
| `npm run preview` | Preview the production build       |

## Configuration

- In development, API calls use the relative `/api` path (proxied to the backend).
- In production, set `VITE_API_URL` to your deployed backend URL.

## Features

- Login / registration (JWT stored in localStorage)
- Dashboard and chat pages with protected routing
- Chat with typing indicator, persisted history and clear-chat
- Voice input (Web Speech API, Chrome/Edge)
- Text-to-speech for AI answers
- Dark mode toggle
- SOS emergency information modal
- Admin document management panel (upload / list / delete)

## Structure

```
src/
├── App.jsx        # routing, auth state, navbar, theme
├── Login.jsx      # login / register
├── Dashboard.jsx  # welcome + feature cards
├── Chat.jsx       # chat UI + extra features
├── api.js         # axios client with auth interceptor
└── styles.css     # medical theme, dark mode, responsive
```
