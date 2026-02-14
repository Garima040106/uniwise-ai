import requests
import json
import time
from django.conf import settings
from .rag import query_rag


def query_ollama(prompt, system_prompt=None, max_retries=3):
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=120)
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


def build_rag_context(query, university_id, course_id=None):
    """
    Retrieve relevant chunks from university docs only
    """
    results = query_rag(query, university_id, course_id)
    if not results:
        return "", []

    context = "\n\n".join([
        f"[From: {r['source']}]\n{r['content']}"
        for r in results
    ])
    sources = list(set([r['source'] for r in results]))
    return context, sources


def generate_flashcards(text, university_id=None, course_id=None, num_cards=10, difficulty="medium"):
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
            "key concepts and definitions", university_id, course_id
        )
        if context:
            text = context

    prompt = f"""Generate {num_cards} flashcards from this university content at {difficulty} difficulty.

IMPORTANT: Only use information from the content below. Do not add external knowledge.

Content:
{text[:4000]}

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
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    return []


def generate_quiz(text, university_id=None, course_id=None, num_questions=5, difficulty="medium"):
    """
    Generate quiz using RAG - only from university docs
    """
    system_prompt = """You are a university professor creating exam questions.
    Create questions ONLY from the provided content.
    Do NOT use any external knowledge.
    Always respond in valid JSON format only."""

    if university_id:
        context, sources = build_rag_context(
            "important facts and concepts for exam", university_id, course_id
        )
        if context:
            text = context

    prompt = f"""Generate {num_questions} multiple choice questions from this university content at {difficulty} difficulty.

IMPORTANT: Only use information from the content below.

Content:
{text[:4000]}

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
            return json.loads(response[start:end])
    except json.JSONDecodeError:
        pass
    return []


def generate_summary(text, university_id=None, course_id=None, max_points=8):
    """Generate exam prep summary from university docs only"""
    system_prompt = """You are an academic summarizer for universities.
    Summarize ONLY from the provided content.
    Always respond in valid JSON format only."""

    if university_id:
        context, sources = build_rag_context(
            "main topics and key points", university_id, course_id
        )
        if context:
            text = context

    prompt = f"""Create an exam preparation summary from this university content with {max_points} key points.

IMPORTANT: Only use information from the content below.

Content:
{text[:4000]}

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


def extract_facts(text, university_id=None, course_id=None, num_facts=10):
    """Extract facts from university docs only"""
    system_prompt = """You are extracting academic facts for university students.
    Extract facts ONLY from the provided content.
    Always respond in valid JSON format only."""

    if university_id:
        context, sources = build_rag_context(
            "facts figures and definitions", university_id, course_id
        )
        if context:
            text = context

    prompt = f"""Extract {num_facts} key facts from this university content.

IMPORTANT: Only extract from the content below.

Content:
{text[:4000]}

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
