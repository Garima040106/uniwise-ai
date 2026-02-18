import os
import chromadb
from chromadb.utils import embedding_functions
from django.conf import settings

_CHROMA_CLIENT = None
_EMBEDDING_FUNCTION = None
_COLLECTION_CACHE = {}


# Initialize ChromaDB client
def get_chroma_client():
    global _CHROMA_CLIENT
    if _CHROMA_CLIENT is not None:
        return _CHROMA_CLIENT

    persist_dir = str(settings.CHROMA_PERSIST_DIRECTORY)
    os.makedirs(persist_dir, exist_ok=True)
    _CHROMA_CLIENT = chromadb.PersistentClient(path=persist_dir)
    return _CHROMA_CLIENT


def get_embedding_function():
    global _EMBEDDING_FUNCTION
    if _EMBEDDING_FUNCTION is not None:
        return _EMBEDDING_FUNCTION

    _EMBEDDING_FUNCTION = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return _EMBEDDING_FUNCTION


def get_or_create_collection(university_id, course_id=None):
    """
    Each university gets its own isolated collection
    Students can ONLY access their university's collection
    """
    # Collection name based on university (isolated per university!)
    if course_id:
        collection_name = f"uni_{university_id}_course_{course_id}"
    else:
        collection_name = f"uni_{university_id}"

    if collection_name in _COLLECTION_CACHE:
        return _COLLECTION_CACHE[collection_name]

    client = get_chroma_client()
    ef = get_embedding_function()

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata={"university_id": str(university_id)}
    )
    _COLLECTION_CACHE[collection_name] = collection
    return collection


def add_document_to_rag(document, chunks, university_id, course_id=None):
    """
    Professor uploads doc → stored in university's isolated RAG collection
    """
    collection = get_or_create_collection(university_id, course_id)

    texts = []
    ids = []
    metadatas = []

    for chunk in chunks:
        texts.append(chunk.content)
        ids.append(f"doc_{document.id}_chunk_{chunk.chunk_index}")
        metadatas.append({
            "document_id": str(document.id),
            "document_title": document.title,
            "chunk_index": str(chunk.chunk_index),
            "university_id": str(university_id),
        })

    if texts:
        collection.upsert(
            documents=texts,
            ids=ids,
            metadatas=metadatas,
        )
        return len(texts)
    return 0


def query_rag(query_text, university_id, course_id=None, n_results=5, document_id=None):
    """
    Query ONLY the university's documents — fully constrained RAG
    Students only get answers from their university's uploaded content
    """
    try:
        collection = get_or_create_collection(university_id, course_id)
        query_kwargs = {
            "query_texts": [query_text],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if document_id is not None:
            query_kwargs["where"] = {"document_id": str(document_id)}

        results = collection.query(**query_kwargs)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        max_distance = getattr(settings, "RAG_MAX_DISTANCE", 1.2)

        context_pieces = []
        for doc, meta, distance in zip(documents, metadatas, distances):
            if distance is not None and distance > max_distance:
                continue
            context_pieces.append({
                "content": doc,
                "source": meta.get("document_title", "Unknown"),
                "chunk": meta.get("chunk_index", "0"),
                "distance": distance,
            })
        return context_pieces

    except Exception as e:
        print(f"RAG query error: {e}")
        return []


def delete_document_from_rag(document_id, university_id, course_id=None):
    """Remove a document from RAG when deleted"""
    try:
        collection = get_or_create_collection(university_id, course_id)
        collection.delete(where={"document_id": str(document_id)})
        return True
    except Exception as e:
        print(f"RAG delete error: {e}")
        return False
