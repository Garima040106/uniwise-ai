# PRD: Uniwise AI Engine (AI Study Generation + RAG Q&A)

## Document Control
- Version: v1.0 (Draft)
- Date: February 25, 2026
- Owner: Backend + AI Platform
- Status: Implementation-aligned PRD (current + near-term tightening)

## 1. Product Summary
Uniwise AI helps students convert uploaded university documents into study artifacts and answers, constrained to institutional content. The AI Engine provides six core capabilities:
- AI service health status
- Flashcard generation
- Quiz generation
- Exam prep summary generation
- Concept/fact extraction
- RAG-based Q&A from university documents

## 2. Problem Statement
Students work with large course documents and need fast, reliable study support without hallucinated or off-syllabus answers.

Current pain points:
- Manual study material creation is slow.
- Students cannot easily assess coverage.
- Generic AI answers may be inaccurate for their syllabus.
- CPU-only deployments can be slow and failure-prone.

## 3. Goals
- Generate high-quality, document-grounded flashcards and quizzes.
- Provide university-scoped Q&A with source traceability.
- Keep generation workflows simple: select document, choose difficulty/count, generate.
- Gracefully handle model slowness/failure with actionable errors.

## 4. Non-Goals (v1)
- Cross-university retrieval
- External web knowledge integration
- Adaptive study-path orchestration beyond current analytics
- Professor-curated question-bank workflow

## 5. Users
- Student: Generate study content, ask questions, practice.
- Professor: Upload documents that students use.
- Admin/Ops: Verify AI service availability through status API.

## 6. Core Requirements
- Authentication is required for all generation and Q&A endpoints.
- Retrieval must be constrained to user university scope.
- Generated content must be persisted and linked to the request user and document.
- Duplicate quiz questions for the same user+document should be avoided.
- Responses should include processing metadata where applicable.
- Errors must be explicit and actionable (`404`, `400`, `409`, `503`, `500`).

## 7. API Requirements

| Endpoint | Auth | Requirement |
|---|---|---|
| `GET /api/ai/status/` | AllowAny | Return Ollama availability and configured model status. |
| `POST /api/ai/flashcards/generate/` | IsAuthenticated | Generate `num_cards` flashcards from selected document text and persist them. |
| `POST /api/ai/quiz/generate/` | IsAuthenticated | Generate MCQ quiz with `num_questions`, dedupe against prior document questions, persist quiz + questions. |
| `POST /api/ai/exam-prep/generate/` | IsAuthenticated | Generate summary slide artifact with key points and important facts. |
| `POST /api/ai/facts/extract/` | IsAuthenticated | Extract structured concept/fact/source entries and persist them. |
| `POST /api/ai/ask/` | IsAuthenticated | Answer question using university-scoped RAG only; return answer + source docs + found flag. |

## 8. Quality Requirements
- Grounding: Outputs must come only from uploaded context.
- Coverage: Prompts should encourage syllabus-wide section coverage.
- Robustness: Retry once for generation shortfall; safely parse malformed JSON.
- Privacy/Isolation: University-level retrieval isolation must be enforced.
- UX: Slow CPU inference should return retry guidance.

## 9. Success Metrics
- Generation success rate (`2xx`) per endpoint
- AI failure rate (`503`, timeout, model unavailability)
- Duplicate quiz rejection rate and retry recovery rate
- Average generation latency by artifact type
- Q&A `found_in_docs=true` rate
- Engagement lift: generated artifacts used in attempts/reviews

## 10. Acceptance Criteria
1. Student can generate flashcards from their document and receives persisted cards with IDs.
2. Student can generate a quiz; duplicate-only output returns conflict with clear next action.
3. Student can ask a question and receive a source-attributed answer from university documents only.
4. Unaffiliated users receive a clear error for Q&A access requiring university affiliation.
5. If Ollama/model is unavailable, status endpoint reports offline and generation endpoints fail clearly.
6. All successful artifact generation is retrievable through existing Flashcards/Quizzes flows.

## 11. Risks and Mitigations
- Slow CPU inference can cause timeouts.
  - Mitigation: Smaller default counts and explicit retry messaging.
- Hallucination risk.
  - Mitigation: Strict prompt grounding + source evidence formatting.
- Context truncation on large documents.
  - Mitigation: Balanced chunk sampling + RAG merge strategy.
- Operational fragility in local model runtime.
  - Mitigation: Health endpoint and model-availability checks.

## 12. Proposed v1.1 Improvements
- Track `AIRequest` for exam prep, fact extraction, and ask flows (not just flashcard/quiz).
- Validate `extracted_text` presence consistently across all generation endpoints.
- Add idempotency key support to avoid accidental duplicate generations.
- Add per-endpoint rate limits and a standardized error schema.
- Return richer source references in Q&A (`document_id`, chunk IDs).

## 13. Reference Scope
This PRD is aligned with:
- `backend/ai_engine/views.py`
- `backend/ai_engine/utils.py`
- `backend/ai_engine/rag.py`
- `backend/ai_engine/models.py`
- Related integration models in `backend/documents`, `backend/quizzes`, and `backend/flashcards`
