import requests
import json
import time
import re
from django.conf import settings
from .rag import query_rag


def query_ollama(prompt, system_prompt=None, max_retries=None):
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

    if max_retries is None:
        max_retries = settings.OLLAMA_MAX_RETRIES

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": settings.OLLAMA_NUM_PREDICT,
        },
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=settings.OLLAMA_REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                return "Error: Ollama is not running. Please start it with 'ollama serve'"
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                return "Error: Request timed out."
        except Exception as e:
            return f"Error: {str(e)}"
        time.sleep(2)


def build_rag_context(query, university_id, course_id=None, document_id=None):
    """
    Retrieve relevant chunks from university docs only
    """
    results = query_rag(query, university_id, course_id, document_id=document_id)
    if not results:
        return "", []

    context = "\n\n".join([
        f"[From: {r['source']}]\n{r['content']}"
        for r in results
    ])
    sources = list(set([r['source'] for r in results]))
    return context, sources


def _extract_term_from_question(question):
    q = (question or "").strip()
    patterns = [
        r"^\s*define\s+(.+?)\s*[?.!]?\s*$",
        r"^\s*what is\s+(.+?)\s*[?.!]?\s*$",
        r"^\s*explain\s+(.+?)\s*[?.!]?\s*$",
    ]
    for pattern in patterns:
        match = re.match(pattern, q, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return q


def _find_context_sentence(context_text, term):
    if not context_text or not term:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", context_text)
    term_lower = term.lower()
    for sentence in sentences:
        cleaned = sentence.strip()
        if term_lower in cleaned.lower() and 35 <= len(cleaned) <= 240:
            return cleaned
    return ""


def _normalize_flashcards(cards, context_text, difficulty):
    normalized = []
    for card in cards:
        question = (card.get("question") or "").strip()
        answer = (card.get("answer") or "").strip()
        if not question:
            continue

        term = _extract_term_from_question(question)
        answer_lower = answer.lower()
        low_quality = (
            len(answer.split()) < 4
            or answer_lower.startswith("definition of ")
            or answer_lower == term.lower()
        )

        if low_quality:
            context_sentence = _find_context_sentence(context_text, term)
            if context_sentence:
                answer = context_sentence

        if len(answer.split()) < 4:
            continue

        normalized.append({
            "question": question,
            "answer": answer,
            "difficulty": card.get("difficulty", difficulty),
        })

    return normalized


def _normalize_quiz_questions(questions, difficulty):
    normalized = []
    seen_questions = set()

    def fallback_option_text(question_text, slot):
        term = _extract_term_from_question(question_text)
        label = term if term else "the topic"
        templates = [
            f"A partial interpretation of {label} from a different context",
            f"A general statement about {label} without document support",
            f"A narrower view of {label} focused on one scenario",
            f"A broader assumption about {label} beyond the passage",
        ]
        return templates[slot % len(templates)]

    for q in questions:
        question_text = (q.get("question") or "").strip()
        if not question_text:
            continue

        normalized_key = re.sub(r"\s+", " ", question_text).strip().lower()
        if normalized_key in seen_questions:
            continue
        seen_questions.add(normalized_key)

        option_a = (q.get("option_a") or "").strip()
        option_b = (q.get("option_b") or "").strip()
        option_c = (q.get("option_c") or "").strip()
        option_d = (q.get("option_d") or "").strip()

        options = [option_a, option_b, option_c, option_d]
        used = {opt.lower() for opt in options if opt}

        # Ensure all 4 options exist and look like normal distractors.
        for idx, value in enumerate(options):
            if value:
                continue
            candidate = fallback_option_text(question_text, idx)
            bump = 1
            while candidate.lower() in used:
                candidate = f"{candidate} ({bump})"
                bump += 1
            options[idx] = candidate
            used.add(candidate.lower())

        option_a, option_b, option_c, option_d = options

        correct_answer = str(q.get("correct_answer", "A")).strip().upper()
        if correct_answer not in {"A", "B", "C", "D"}:
            correct_answer = "A"

        normalized.append({
            "question": question_text,
            "option_a": option_a,
            "option_b": option_b,
            "option_c": option_c,
            "option_d": option_d,
            "correct_answer": correct_answer,
            "explanation": (q.get("explanation") or "").strip(),
            "difficulty": difficulty,
        })

    return normalized


def _build_balanced_document_context(text, num_questions, max_chars):
    """
    Build a compact context that samples evenly across the full document.
    This keeps prompt size bounded while improving syllabus-wide coverage.
    """
    clean_text = re.sub(r"\s+", " ", (text or "")).strip()
    if not clean_text:
        return ""

    if len(clean_text) <= max_chars:
        return clean_text

    section_count = min(max(num_questions, 6), 12)
    label_budget = section_count * 20
    usable_chars = max(600, max_chars - label_budget)
    snippet_size = max(120, usable_chars // section_count)
    max_start = max(0, len(clean_text) - snippet_size)

    sections = []
    for i in range(section_count):
        start = int((max_start * i) / max(section_count - 1, 1))
        end = min(len(clean_text), start + snippet_size)
        snippet = clean_text[start:end].strip()
        if not snippet:
            continue
        sections.append(f"[S{i + 1}] {snippet}")

    balanced = "\n".join(sections).strip()
    return balanced[:max_chars]


def generate_flashcards(text, university_id=None, course_id=None, document_id=None, num_cards=10, difficulty="medium"):
    """
    Generate flashcards using RAG - only from university docs
    """
    system_prompt = """You are an expert educational content creator for universities.
    Generate flashcards ONLY based on the provided context.
    Do NOT use any external knowledge.
    Always respond in valid JSON format only."""

    # Use RAG if university_id provided
    if university_id:
        context, sources = build_rag_context(
            "key concepts and explicit definitions from the selected document",
            university_id,
            course_id,
            document_id=document_id,
        )
        if context:
            text = context

    prompt = f"""Generate {num_cards} flashcards from this university content at {difficulty} difficulty.

IMPORTANT: Only use information from the content below. Do not add external knowledge.
Each answer must be a complete explanatory statement, not a title or label.
For easy difficulty, answers must be 1-2 full sentences and at least 10 words.

Content:
{text[:settings.AI_CONTEXT_CHAR_LIMIT]}

Respond ONLY with a JSON array:
[
  {{
    "question": "What is...",
    "answer": "Based on the document...",
    "difficulty": "{difficulty}"
  }}
]"""

    response = query_ollama(prompt, system_prompt)

    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end != 0:
            cards = json.loads(response[start:end])
            return _normalize_flashcards(cards, text, difficulty)
    except json.JSONDecodeError:
        pass
    return []


def generate_quiz(
    text,
    university_id=None,
    course_id=None,
    document_id=None,
    num_questions=5,
    difficulty="medium",
    excluded_questions=None,
):
    """
    Generate quiz using RAG - only from university docs
    """
    system_prompt = """You are a university professor creating exam questions.
    Create questions ONLY from the provided content.
    Do NOT use any external knowledge.
    Always respond in valid JSON format only."""

    # Keep original document text so we can preserve whole-syllabus coverage.
    full_document_text = text or ""
    context_text = full_document_text

    if university_id:
        context, sources = build_rag_context(
            "important facts and concepts for exam",
            university_id,
            course_id,
            document_id=document_id,
        )
        if context:
            # Blend high-signal RAG snippets with full document coverage.
            context_text = f"{context}\n\n{full_document_text}"

    balanced_context = _build_balanced_document_context(
        context_text,
        num_questions=num_questions,
        max_chars=settings.AI_CONTEXT_CHAR_LIMIT,
    )

    excluded_text = ""
    if excluded_questions:
        excluded_lines = "\n".join([f"- {q}" for q in excluded_questions[:30]])
        excluded_text = (
            "\nDo NOT generate these already-used questions (or close paraphrases):\n"
            f"{excluded_lines}\n"
        )

    prompt = f"""Generate {num_questions} multiple choice questions from this university content at {difficulty} difficulty.

IMPORTANT: Only use information from the content below.
Provide exactly 4 non-empty options (A, B, C, D) for every question.
Do not use placeholders like "Not specified in the document".
Distribute questions across different sections of the content so the syllabus is broadly covered.
Avoid repeating the same concept in multiple questions.
{excluded_text}

Content:
{balanced_context}

Respond ONLY with a JSON array:
[
  {{
    "question": "According to the document...",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_answer": "A",
    "explanation": "According to the document..."
  }}
]"""

    response = query_ollama(prompt, system_prompt)

    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end != 0:
            questions = json.loads(response[start:end])
            return _normalize_quiz_questions(questions, difficulty)
    except json.JSONDecodeError:
        pass
    return []


def generate_summary(text, university_id=None, course_id=None, document_id=None, max_points=8):
    """Generate exam prep summary from university docs only"""
    system_prompt = """You are an academic summarizer for universities.
    Summarize ONLY from the provided content.
    Always respond in valid JSON format only."""

    if university_id:
        context, sources = build_rag_context(
            "main topics and key points",
            university_id,
            course_id,
            document_id=document_id,
        )
        if context:
            text = context

    prompt = f"""Create an exam preparation summary from this university content with {max_points} key points.

IMPORTANT: Only use information from the content below.

Content:
{text[:settings.AI_CONTEXT_CHAR_LIMIT]}

Respond ONLY with JSON:
{{
  "title": "Topic Title",
  "key_points": ["Point 1", "Point 2"],
  "important_facts": ["Fact 1", "Fact 2"]
}}"""

    response = query_ollama(prompt, system_prompt)

    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end != 0:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    return {}


def extract_facts(text, university_id=None, course_id=None, document_id=None, num_facts=10):
    """Extract facts from university docs only"""
    system_prompt = """You are extracting academic facts for university students.
    Extract facts ONLY from the provided content.
    Always respond in valid JSON format only."""

    if university_id:
        context, sources = build_rag_context(
            "facts figures and definitions",
            university_id,
            course_id,
            document_id=document_id,
        )
        if context:
            text = context

    prompt = f"""Extract {num_facts} key facts from this university content.

IMPORTANT: Only extract from the content below.

Content:
{text[:settings.AI_CONTEXT_CHAR_LIMIT]}

Respond ONLY with a JSON array:
[
  {{
    "concept": "Concept name",
    "fact": "The fact from the document",
    "source_text": "Brief quote"
  }}
]"""

    response = query_ollama(prompt, system_prompt)

    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end != 0:
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    return []


def answer_question_rag(question, university_id, course_id=None):
    """
    Answer a student question using ONLY university documents
    This is the core RAG Q&A feature
    """
    context, sources = build_rag_context(question, university_id, course_id)

    if not context:
        return {
            "answer": "I could not find relevant information in your university's documents. Please ask your professor to upload relevant materials.",
            "sources": [],
            "found_in_docs": False,
        }

    system_prompt = """You are a university AI assistant.
    Answer questions ONLY using the provided university documents.
    If the answer is not in the documents, say so clearly.
    Never use external knowledge."""

    prompt = f"""Answer this student question using ONLY the university documents below.

Question: {question}

University Documents:
{context}

Provide a clear, educational answer based strictly on the above documents."""

    answer = query_ollama(prompt, system_prompt)

    return {
        "answer": answer,
        "sources": sources,
        "found_in_docs": True,
    }
