import os
import chromadb
from chromadb.utils import embedding_functions
from django.conf import settings


# Initialize ChromaDB client
def get_chroma_client():
    persist_dir = str(settings.CHROMA_PERSIST_DIRECTORY)
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def get_embedding_function():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def get_or_create_collection(university_id, course_id=None):
    """
    Each university gets its own isolated collection
    Students can ONLY access their university's collection
    """
    client = get_chroma_client()
    ef = get_embedding_function()

    # Collection name based on university (isolated per university!)
    if course_id:
        collection_name = f"uni_{university_id}_course_{course_id}"
    else:
        collection_name = f"uni_{university_id}"

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata={"university_id": str(university_id)}
    )
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


def query_rag(query_text, university_id, course_id=None, n_results=5):
    """
    Query ONLY the university's documents — fully constrained RAG
    Students only get answers from their university's uploaded content
    """
    try:
        collection = get_or_create_collection(university_id, course_id)
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        context_pieces = []
        for doc, meta in zip(documents, metadatas):
            context_pieces.append({
                "content": doc,
                "source": meta.get("document_title", "Unknown"),
                "chunk": meta.get("chunk_index", "0"),
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
