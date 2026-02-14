import requests
import json
import time
from django.conf import settings


def query_ollama(prompt, system_prompt=None, max_retries=3):
    """
    Core function to query Ollama LLM
    """
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
                return "Error: Request timed out. Model may be overloaded."
        except Exception as e:
            return f"Error: {str(e)}"
        time.sleep(2)


def generate_flashcards(text, num_cards=10, difficulty="medium"):
    """
    Generate flashcards from text using Ollama
    """
    system_prompt = """You are an expert educational content creator. 
    Generate clear, concise flashcards for university students.
    Always respond in valid JSON format only."""

    prompt = f"""Generate {num_cards} flashcards from this text at {difficulty} difficulty level.

Text: {text[:3000]}

Respond ONLY with a JSON array in this exact format:
[
  {{
    "question": "What is...",
    "answer": "The answer is...",
    "difficulty": "{difficulty}"
  }}
]"""

    response = query_ollama(prompt, system_prompt)
    
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end != 0:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return []


def generate_quiz(text, num_questions=5, difficulty="medium"):
    """
    Generate quiz questions from text using Ollama
    """
    system_prompt = """You are an expert university professor creating exam questions.
    Generate clear multiple choice questions.
    Always respond in valid JSON format only."""

    prompt = f"""Generate {num_questions} multiple choice questions from this text at {difficulty} difficulty.

Text: {text[:3000]}

Respond ONLY with a JSON array in this exact format:
[
  {{
    "question": "What is...",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_answer": "A",
    "explanation": "The correct answer is A because..."
  }}
]"""

    response = query_ollama(prompt, system_prompt)
    
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end != 0:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return []


def generate_summary(text, max_points=8):
    """
    Generate exam prep summary/slides from text
    """
    system_prompt = """You are an expert academic summarizer.
    Create concise exam preparation summaries for university students.
    Always respond in valid JSON format only."""

    prompt = f"""Create an exam preparation summary from this text with {max_points} key points.

Text: {text[:3000]}

Respond ONLY with JSON in this exact format:
{{
  "title": "Topic Title",
  "key_points": [
    "First key point...",
    "Second key point..."
  ],
  "important_facts": [
    "Important fact 1",
    "Important fact 2"
  ]
}}"""

    response = query_ollama(prompt, system_prompt)
    
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end != 0:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return {}


def extract_facts(text, num_facts=10):
    """
    Extract key conceptual facts and figures from text
    """
    system_prompt = """You are an expert at extracting key academic facts.
    Extract important concepts, facts and figures for university students.
    Always respond in valid JSON format only."""

    prompt = f"""Extract {num_facts} key facts and concepts from this text.

Text: {text[:3000]}

Respond ONLY with a JSON array in this exact format:
[
  {{
    "concept": "Concept name",
    "fact": "The fact or definition",
    "source_text": "Brief quote from source"
  }}
]"""

    response = query_ollama(prompt, system_prompt)
    
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end != 0:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return []
