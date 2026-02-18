# Uniwise AI

Uniwise AI is a study assistant for university students that turns uploaded documents into:
- Flashcards
- Quizzes
- Focused Q&A (RAG-based answers from uploaded content)
- Progress tracking on the dashboard

The project uses a Django backend, a React frontend, PostgreSQL, ChromaDB for vector retrieval, and Ollama (`llama3.2:3b`) for generation.

## What This Project Solves

Students often upload large PDFs and don’t know if they’ve actually covered the syllabus.  
Uniwise AI helps by generating study material from documents and showing progress based on attempted quiz/flashcard coverage.

## Current Features

- Document upload and indexing (PDF/DOCX/TXT/PPTX)
- University-isolated RAG retrieval
- Quiz generation with improved section coverage across the document
- Flashcard generation
- Quiz completion and result analysis (accuracy, weak areas, recommendation)
- Delete actions for flashcards/quizzes/documents
- Dashboard with:
  - AI status
  - overall stats
  - document-wise coverage score (1–100)

## Tech Stack

- Backend: Django + Django REST Framework
- Frontend: React (CRA)
- Database: PostgreSQL
- Vector Store: ChromaDB
- LLM runtime: Ollama
- Containerization: Docker Compose

## Repository Structure

```text
backend/      Django apps (accounts, documents, ai_engine, quizzes, analytics, ...)
frontend/     React app
docker-compose.yml
requirements.txt
```

## Local Run (Recommended)

### 1) Start backend services

```bash
docker compose up -d
docker compose ps
```

Backend API will be available at: `http://localhost:8000`

### 2) Start frontend

```bash
cd frontend
npm install
npm start
```

Frontend will run at: `http://localhost:3000`

## Typical Testing Flow

1. Login (student/admin)
2. Upload a document from **Documents**
3. Generate flashcards or a quiz
4. Submit quiz and check analysis block
5. Open **Dashboard → Document Progress** and verify coverage score

## API Notes

- Base URL: `/api`
- Key routes:
  - `/api/documents/*`
  - `/api/ai/*`
  - `/api/quizzes/*`
  - `/api/analytics/*`

## Environment Notes

This setup is usable on CPU-only systems, but generation can be slower.  
For faster iterations, start with fewer generated items (for example 2–3 questions/cards).

## Security / Access Model

- Student view is constrained to their university/document scope for RAG.
- Planned next step: **professor-only question-bank upload and retrieval** (separate flow and role-gated access).

## Known Practical Constraints

- Large document generation quality depends on model context budget.
- CPU-only inference may increase response time for longer prompts.

## Status

This repository is actively evolving. The current version is focused on reliable student workflows first (upload → generate → practice → track).
