import json
import re
import time
from collections import OrderedDict

import requests
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


def _clean_text(value):
    return " ".join((value or "").split()).strip()


def _extract_json_candidate(response_text, start_char, end_char):
    text = (response_text or "").strip()
    if not text:
        return ""

    start = text.find(start_char)
    end = text.rfind(end_char)
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start:end + 1]


def _safe_json_loads(candidate):
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Common recovery: remove trailing commas before ] or }.
        repaired = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None


def _parse_json_array(response_text):
    candidate = _extract_json_candidate(response_text, "[", "]")
    parsed = _safe_json_loads(candidate)
    if isinstance(parsed, list):
        return parsed
    return []


def _parse_json_object(response_text):
    candidate = _extract_json_candidate(response_text, "{", "}")
    parsed = _safe_json_loads(candidate)
    if isinstance(parsed, dict):
        return parsed
    return {}


def _dedupe_sources(results):
    ordered = OrderedDict()
    for item in results:
        source = item.get("source")
        if source and source not in ordered:
            ordered[source] = True
    return list(ordered.keys())


def _format_rag_context(results, max_chars):
    if not results:
        return "", []

    pieces = []
    used_results = []
    consumed = 0

    for rank, item in enumerate(results, start=1):
        source = item.get("source", "Unknown")
        chunk = item.get("chunk", "0")
        content = _clean_text(item.get("content", ""))
        if not content:
            continue

        piece = f"[R{rank} | {source} | chunk {chunk}]\n{content}"
        if pieces and consumed + len(piece) + 2 > max_chars:
            break
        if not pieces and len(piece) > max_chars:
            piece = piece[:max_chars]
        pieces.append(piece)
        used_results.append(item)
        consumed += len(piece) + 2

    return "\n\n".join(pieces), _dedupe_sources(used_results)


def build_rag_context(query, university_id, course_id=None, document_id=None, n_results=8, max_chars=None):
    """
    Retrieve and format high-signal chunks from university docs only.
    """
    if max_chars is None:
        max_chars = settings.AI_CONTEXT_CHAR_LIMIT

    results = query_rag(
        query_text=query,
        university_id=university_id,
        course_id=course_id,
        n_results=n_results,
        document_id=document_id,
    )
    return _format_rag_context(results, max_chars=max_chars)


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
    seen = set()

    for card in cards:
        if not isinstance(card, dict):
            continue
        question = _clean_text(card.get("question", ""))
        answer = _clean_text(card.get("answer", ""))
        if not question:
            continue

        if not question.endswith("?"):
            question = f"{question}?"

        q_key = question.lower()
        if q_key in seen:
            continue
        seen.add(q_key)

        term = _extract_term_from_question(question)
        answer_lower = answer.lower()
        low_quality = (
            len(answer.split()) < 6
            or answer_lower.startswith("definition of ")
            or answer_lower == term.lower()
        )

        if low_quality:
            context_sentence = _find_context_sentence(context_text, term)
            if context_sentence:
                answer = _clean_text(context_sentence)

        if len(answer.split()) < 6:
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
        if not isinstance(q, dict):
            continue
        question_text = _clean_text(q.get("question", ""))
        if not question_text:
            continue

        normalized_key = re.sub(r"\s+", " ", question_text).strip().lower()
        if normalized_key in seen_questions:
            continue
        seen_questions.add(normalized_key)

        option_a = _clean_text(q.get("option_a", ""))
        option_b = _clean_text(q.get("option_b", ""))
        option_c = _clean_text(q.get("option_c", ""))
        option_d = _clean_text(q.get("option_d", ""))

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

        explanation = _clean_text(q.get("explanation", ""))
        if not explanation:
            correct_option = options[ord(correct_answer) - ord("A")]
            explanation = f"This matches the document context: {correct_option}"

        normalized.append({
            "question": question_text,
            "option_a": option_a,
            "option_b": option_b,
            "option_c": option_c,
            "option_d": option_d,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "difficulty": difficulty,
        })

    return normalized


def _nearest_sentence_start(text, index):
    if index <= 0:
        return 0
    left = max(0, index - 120)
    window = text[left:index]
    boundary = max(window.rfind("."), window.rfind("!"), window.rfind("?"), window.rfind("\n"))
    if boundary == -1:
        return index
    return left + boundary + 1


def _nearest_sentence_end(text, index):
    if index >= len(text):
        return len(text)
    right = min(len(text), index + 140)
    window = text[index:right]
    boundary_positions = [window.find("."), window.find("!"), window.find("?"), window.find("\n")]
    boundary_positions = [pos for pos in boundary_positions if pos != -1]
    if not boundary_positions:
        return index
    return index + min(boundary_positions) + 1


def _build_balanced_document_context(text, section_hint, max_chars):
    """
    Build a compact context that samples evenly across the full document.
    This keeps prompt size bounded while improving syllabus-wide coverage.
    """
    clean_text = re.sub(r"\s+", " ", (text or "")).strip()
    if not clean_text:
        return ""

    if len(clean_text) <= max_chars:
        return clean_text

    section_count = min(max(section_hint, 6), 14)
    label_budget = section_count * 20
    usable_chars = max(600, max_chars - label_budget)
    snippet_size = max(120, usable_chars // section_count)
    max_start = max(0, len(clean_text) - snippet_size)

    sections = []
    seen = set()
    for i in range(section_count):
        start = int((max_start * i) / max(section_count - 1, 1))
        start = _nearest_sentence_start(clean_text, start)
        end = min(len(clean_text), start + snippet_size)
        end = _nearest_sentence_end(clean_text, end)
        snippet = clean_text[start:end].strip()
        snippet_key = snippet.lower()
        if not snippet or snippet_key in seen:
            continue
        seen.add(snippet_key)
        sections.append(f"[S{i + 1}] {snippet}")

    balanced = "\n".join(sections).strip()
    return balanced[:max_chars]


def _merge_context_fragments(*parts):
    merged = []
    for part in parts:
        cleaned = (part or "").strip()
        if cleaned:
            merged.append(cleaned)
    return "\n\n".join(merged).strip()


def _build_study_context(
    base_text,
    objective,
    university_id=None,
    course_id=None,
    document_id=None,
    section_hint=8,
    rag_results=8,
):
    max_chars = settings.AI_CONTEXT_CHAR_LIMIT
    rag_budget = int(max_chars * 0.55) if university_id else 0
    coverage_budget = max_chars - rag_budget if rag_budget else max_chars
    rag_chunk_budget = min(max_chars, max(180, rag_budget)) if rag_budget else 0
    coverage_chunk_budget = min(max_chars, max(180, coverage_budget))

    rag_context = ""
    sources = []
    if university_id:
        rag_context, sources = build_rag_context(
            query=objective,
            university_id=university_id,
            course_id=course_id,
            document_id=document_id,
            n_results=rag_results,
            max_chars=rag_chunk_budget,
        )

    coverage_context = _build_balanced_document_context(
        text=base_text,
        section_hint=section_hint,
        max_chars=coverage_chunk_budget,
    )

    final_context = _merge_context_fragments(
        f"High-relevance retrieved excerpts:\n{rag_context}" if rag_context else "",
        f"Coverage excerpts sampled across the full document:\n{coverage_context}" if coverage_context else "",
    )

    if len(final_context) > max_chars:
        final_context = final_context[:max_chars]

    return final_context, sources


def _merge_unique_by_key(existing_items, new_items, key_fn):
    existing_keys = {key_fn(item) for item in existing_items}
    for item in new_items:
        item_key = key_fn(item)
        if item_key in existing_keys:
            continue
        existing_items.append(item)
        existing_keys.add(item_key)
    return existing_items


def generate_flashcards(text, university_id=None, course_id=None, document_id=None, num_cards=10, difficulty="medium"):
    """
    Generate flashcards using RAG - only from university docs
    """
    system_prompt = """You are an expert educational content creator for universities.
    Generate flashcards ONLY based on the provided context.
    Do NOT use any external knowledge.
    Always respond in valid JSON format only."""

    context_text, _ = _build_study_context(
        base_text=text,
        objective="definitions, formulas, key concepts, causes, effects, and examples",
        university_id=university_id,
        course_id=course_id,
        document_id=document_id,
        section_hint=max(num_cards, 8),
        rag_results=max(8, num_cards + 2),
    )
    if not context_text:
        context_text = (text or "")[:settings.AI_CONTEXT_CHAR_LIMIT]

    prompt = f"""Generate exactly {num_cards} flashcards from this university content at {difficulty} difficulty.

IMPORTANT: Only use information from the content below. Do not add external knowledge.
Each answer must be a complete explanatory statement, not a title or label.
Cover different parts of the content (beginning, middle, end), not just one section.
For easy difficulty, answers must be 1-2 full sentences and at least 10 words.

Content:
{context_text}

Respond ONLY with a JSON array:
[
  {{
    "question": "What is...",
    "answer": "Based on the document...",
    "difficulty": "{difficulty}"
  }}
]"""

    cards = []
    for attempt in range(2):
        if attempt == 1:
            prompt = f"""Return ONLY a JSON array with exactly {num_cards - len(cards)} additional flashcards not overlapping previous ones.

Previous flashcard questions to avoid:
{json.dumps([item["question"] for item in cards], ensure_ascii=True)}

Content:
{context_text}

JSON schema:
[
  {{
    "question": "Question?",
    "answer": "Clear answer from the document",
    "difficulty": "{difficulty}"
  }}
]
"""

        response = query_ollama(prompt, system_prompt)
        parsed = _parse_json_array(response)
        normalized = _normalize_flashcards(parsed, context_text, difficulty)
        cards = _merge_unique_by_key(cards, normalized, key_fn=lambda c: c["question"].lower())
        if len(cards) >= num_cards:
            break

    return cards[:num_cards]


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

    context_text, _ = _build_study_context(
        base_text=text,
        objective="important facts, concepts, relationships, formulas, and edge cases for exam practice",
        university_id=university_id,
        course_id=course_id,
        document_id=document_id,
        section_hint=max(num_questions + 2, 8),
        rag_results=max(10, num_questions + 4),
    )
    if not context_text:
        context_text = (text or "")[:settings.AI_CONTEXT_CHAR_LIMIT]

    excluded_text = ""
    if excluded_questions:
        excluded_lines = "\n".join([f"- {q}" for q in excluded_questions[:30]])
        excluded_text = (
            "\nDo NOT generate these already-used questions (or close paraphrases):\n"
            f"{excluded_lines}\n"
        )

    prompt = f"""Generate exactly {num_questions} multiple choice questions from this university content at {difficulty} difficulty.

IMPORTANT: Only use information from the content below.
Provide exactly 4 non-empty options (A, B, C, D) for every question.
Do not use placeholders like "Not specified in the document".
Distribute questions across different sections of the content so the syllabus is broadly covered.
Avoid repeating the same concept in multiple questions.
{excluded_text}

Content:
{context_text}

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

    normalized_questions = []
    excluded_set = set(q.lower().strip() for q in (excluded_questions or []))

    for attempt in range(2):
        if attempt == 1:
            avoid = [item["question"] for item in normalized_questions]
            retry_exclusions = excluded_set.union({q.lower() for q in avoid})
            retry_lines = "\n".join(f"- {q}" for q in sorted(retry_exclusions)[:50])
            prompt = f"""Generate exactly {num_questions - len(normalized_questions)} additional MCQ questions.
Do NOT repeat these questions or close paraphrases:
{retry_lines}

Content:
{context_text}

Respond ONLY with a JSON array using this schema:
[
  {{
    "question": "Question text",
    "option_a": "Option A",
    "option_b": "Option B",
    "option_c": "Option C",
    "option_d": "Option D",
    "correct_answer": "A",
    "explanation": "Brief explanation"
  }}
]
"""

        response = query_ollama(prompt, system_prompt)
        parsed = _parse_json_array(response)
        batch = _normalize_quiz_questions(parsed, difficulty)
        batch = [
            q for q in batch
            if q["question"].lower().strip() not in excluded_set
        ]
        normalized_questions = _merge_unique_by_key(
            normalized_questions,
            batch,
            key_fn=lambda q: q["question"].lower(),
        )
        if len(normalized_questions) >= num_questions:
            break

    return normalized_questions[:num_questions]


def generate_summary(text, university_id=None, course_id=None, document_id=None, max_points=8):
    """Generate exam prep summary from university docs only"""
    system_prompt = """You are an academic summarizer for universities.
    Summarize ONLY from the provided content.
    Always respond in valid JSON format only."""

    context_text, _ = _build_study_context(
        base_text=text,
        objective="main topics, learning objectives, key arguments, and exam-relevant facts",
        university_id=university_id,
        course_id=course_id,
        document_id=document_id,
        section_hint=max(max_points, 8),
        rag_results=max(8, max_points + 2),
    )
    if not context_text:
        context_text = (text or "")[:settings.AI_CONTEXT_CHAR_LIMIT]

    prompt = f"""Create an exam preparation summary from this university content with {max_points} key points.

IMPORTANT: Only use information from the content below.

Content:
{context_text}

Respond ONLY with JSON:
{{
  "title": "Topic Title",
  "key_points": ["Point 1", "Point 2"],
  "important_facts": ["Fact 1", "Fact 2"]
}}"""

    response = query_ollama(prompt, system_prompt)
    summary = _parse_json_object(response)
    if not summary:
        return {}

    raw_key_points = summary.get("key_points", [])
    raw_facts = summary.get("important_facts", [])
    if not isinstance(raw_key_points, list):
        raw_key_points = []
    if not isinstance(raw_facts, list):
        raw_facts = []

    key_points = [_clean_text(point) for point in raw_key_points if _clean_text(point)]
    facts = [_clean_text(fact) for fact in raw_facts if _clean_text(fact)]

    return {
        "title": _clean_text(summary.get("title", "")) or "Document Summary",
        "key_points": key_points[:max_points],
        "important_facts": facts[:max_points],
    }


def extract_facts(text, university_id=None, course_id=None, document_id=None, num_facts=10):
    """Extract facts from university docs only"""
    system_prompt = """You are extracting academic facts for university students.
    Extract facts ONLY from the provided content.
    Always respond in valid JSON format only."""

    context_text, _ = _build_study_context(
        base_text=text,
        objective="facts, figures, definitions, dates, and named concepts",
        university_id=university_id,
        course_id=course_id,
        document_id=document_id,
        section_hint=max(num_facts, 8),
        rag_results=max(8, num_facts + 3),
    )
    if not context_text:
        context_text = (text or "")[:settings.AI_CONTEXT_CHAR_LIMIT]

    prompt = f"""Extract {num_facts} key facts from this university content.

IMPORTANT: Only extract from the content below.

Content:
{context_text}

Respond ONLY with a JSON array:
[
  {{
    "concept": "Concept name",
    "fact": "The fact from the document",
    "source_text": "Brief quote"
  }}
]"""

    response = query_ollama(prompt, system_prompt)
    parsed = _parse_json_array(response)

    facts = []
    seen = set()
    for item in parsed:
        if not isinstance(item, dict):
            continue
        concept = _clean_text(item.get("concept", ""))
        fact = _clean_text(item.get("fact", ""))
        source_text = _clean_text(item.get("source_text", ""))
        if not concept or not fact:
            continue
        key = f"{concept.lower()}::{fact.lower()}"
        if key in seen:
            continue
        seen.add(key)
        if len(source_text.split()) < 5:
            source_text = _find_context_sentence(context_text, concept) or source_text
        facts.append({
            "concept": concept,
            "fact": fact,
            "source_text": source_text,
        })
        if len(facts) >= num_facts:
            break

    return facts


def answer_question_rag(question, university_id, course_id=None, document_id=None):
    """
    Answer a student question using ONLY university documents
    This is the core RAG Q&A feature
    """
    context, sources = build_rag_context(
        query=question,
        university_id=university_id,
        course_id=course_id,
        document_id=document_id,
        n_results=8,
        max_chars=max(settings.AI_CONTEXT_CHAR_LIMIT, 2400),
    )

    if not context:
        return {
            "answer": "I could not find relevant information in your university's documents. Please ask your professor to upload relevant materials.",
            "sources": [],
            "found_in_docs": False,
        }

    system_prompt = """You are a university AI assistant.
    Answer questions ONLY using the provided university documents.
    If the answer is not in the documents, say so clearly.
    Never use external knowledge.
    Keep the tone clear and student-friendly."""

    prompt = f"""Answer this student question using ONLY the university documents below.

Question: {question}

University Documents:
{context}

Respond in this format:
1) Direct answer in 2-5 sentences.
2) "Evidence:" followed by 2-4 bullet points citing chunk labels like [R1], [R2].
3) If evidence is weak/incomplete, add one line: "Limitation: ..."
"""

    answer = query_ollama(prompt, system_prompt)
    if answer.lower().startswith("error:"):
        return {
            "answer": "I could not generate an answer right now because the AI service is unavailable. Please retry in a moment.",
            "sources": sources,
            "found_in_docs": bool(sources),
        }

    return {
        "answer": answer.strip(),
        "sources": sources,
        "found_in_docs": True,
    }
