import os
import PyPDF2
from docx import Document as DocxDocument


def extract_text_from_file(file_path):
    """
    Extract text from uploaded documents
    Supports: PDF, DOCX, TXT
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == ".pdf":
            return extract_from_pdf(file_path)
        elif ext == ".docx":
            return extract_from_docx(file_path)
        elif ext == ".txt":
            return extract_from_txt(file_path)
        else:
            return ""
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""


def extract_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text.strip()


def extract_from_docx(file_path):
    doc = DocxDocument(file_path)
    return "\n".join([para.text for para in doc.paragraphs]).strip()


def extract_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def chunk_text(text, chunk_size=1000, overlap=100):
    """
    Split text into overlapping chunks for processing
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks
