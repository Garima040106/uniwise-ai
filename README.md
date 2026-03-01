# Uniwise AI

Uniwise AI is a university-focused custom LLM platform with:
- Public pre-login guidance for prospective students
- Student and admin authentication flows
- Post-login student learning workspace
- University-scoped RAG for Q&A, flashcards, quizzes, and analytics

The stack uses Django + DRF, React, PostgreSQL, ChromaDB, and Ollama (`llama3.2:3b` by default).

## Product Overview

### 1) Pre-auth experience
- 3-entry hub:
  - Design Your Custom University
  - Student Login
  - Administration Login
- Custom university landing page with:
  - University profile selection (including Indian universities)
  - Branding/theme customization
  - Floating chatbot widget preview
  - Offline-safe AI status handling

### 2) Student authentication
- Student ID + password login
- New student registration
- Forgot/reset password flow
- Optional 2FA login challenge
- SSO provider scaffold (Google and university SSO)

### 3) Student portal
- Dashboard: quick stats, deadlines, recent activity, quick actions
- AI Chatbot tab: simplified prompt-first UI with quick prompt chips
- Learning tools: flashcards, quizzes, document workspace, AI prep
- Progress tracking: skill progress, curve, course-level breakdown
- Additional placeholders: calendar, notifications, profile settings, help

### 4) Admin workspace
- Admin login route and role-gated backend check
- Existing app workspace for dashboard, AI, flashcards, quizzes, documents

### 5) AI + document pipeline
- Upload/index document types: `.pdf`, `.docx`, `.txt`, `.pptx`
- University-isolated retrieval for Q&A
- Flashcard/quiz/exam-prep generation
- Uploads now fail early if text extraction is empty (clear API error message)
- `.pptx` text extraction support is implemented

## Tech Stack

- Backend: Django 5 + Django REST Framework
- Frontend: React (Create React App)
- Database: PostgreSQL (or SQLite for local fallback)
- Vector Store: ChromaDB
- LLM Runtime: Ollama
- Deployment: Docker Compose (dev + prod variants)

## Repository Structure

```text
backend/                  Django apps (accounts, ai_engine, analytics, documents, quizzes, ...)
frontend/                 React app
docker-compose.yml        Local backend + DB stack
docker-compose.prod.yml   Production stack (backend + db + nginx web)
deploy_prod.sh            Production deploy helper
requirements.txt
requirements.prod.txt
```

## Local Development

### Option A: Docker backend + local frontend (recommended)

1) Start backend + PostgreSQL:

```bash
docker compose up -d
docker compose ps
```

Backend API: `http://localhost:8000/api`

2) Start frontend:

```bash
cd frontend
npm install
npm start
```

Frontend: `http://localhost:3000`

### Option B: Run backend without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Production Deployment

Run:

```bash
./deploy_prod.sh
```

This uses `docker-compose.prod.yml` and:
- Runs Django with `uvicorn`
- Applies migrations and collects static files
- Serves React production build with Nginx
- Proxies `/api` and `/admin`
- Persists Postgres/media/static/chroma volumes

App URL: `http://localhost` (or `http://localhost:${WEB_PORT}`)

## Environment Variables

Key variables:
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `MAX_UPLOAD_SIZE`
- `RAG_MAX_DISTANCE`
- `REACT_APP_API_BASE_URL`
- `GOOGLE_OAUTH_CLIENT_ID` (enables Google OAuth redirect mode)
- `SSO_PROVIDERS` (defaults to `google,university-sso`)
- `FRONTEND_RESET_PASSWORD_URL`

Start from `.env.prod.example` for production.

## Quick Test Setup

1) Create a university (if none exists) via Django admin (`/admin`) or shell.
2) Create accounts:
- Student account via UI registration on Student Login page
- Admin account via Django admin or shell (profile role must be `admin`)
3) Login as student and upload a text-based document.
4) Generate flashcards/quizzes and test Ask AI.

## API Surface

Base URL: `/api`

- Accounts: `/api/accounts/*`
  - `register`, `login/student`, `login/admin`, `two-factor/verify`
  - `password/forgot`, `password/reset`
  - `sso/providers`, `sso/start`, `sso/callback`
- Documents: `/api/documents/*`
- AI Engine: `/api/ai/*`
- Flashcards: `/api/flashcards/*`
- Quizzes: `/api/quizzes/*`
- Analytics: `/api/analytics/*`

## Troubleshooting

### "Could not extract text from document"
Cause:
- Scanned/image-only PDF, or document without extractable text.

Fix:
- Re-upload a text-based file (`pdf/docx/txt/pptx`), or OCR the PDF first.
- Check document status in Documents view (`completed` + indexed).

### Ollama shows offline
Check:
- Ollama daemon running
- `OLLAMA_BASE_URL` reachable from backend
- Configured model exists (`ollama list`)

### 2FA code not received
Notes:
- In `DEBUG=True`, API can return `debug_code` for local testing.
- In production, configure email delivery settings.

### SSO returns scaffold response
Notes:
- Current SSO includes provider start/callback scaffolding.
- Set `GOOGLE_OAUTH_CLIENT_ID` for Google OAuth authorization URL mode.

## Known Constraints

- CPU-only inference is slower on long prompts.
- Generation quality depends on extracted document quality and context budget.
- Current flashcard/quiz generation uses documents owned by the authenticated user.

## Status

The platform is actively evolving with a focus on:
- Reliable student learning workflows
- University-specific assistant behavior
- Cleaner UI/UX and clearer onboarding flows
