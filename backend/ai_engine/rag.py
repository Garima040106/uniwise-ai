import os
import re
from collections import OrderedDict, defaultdict

import chromadb
from chromadb.utils import embedding_functions
from django.conf import settings

_CHROMA_CLIENT = None
_EMBEDDING_FUNCTION = None
_COLLECTION_CACHE = {}
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "its", "of", "on", "or", "that", "the", "their", "this",
    "to", "was", "were", "what", "when", "where", "which", "who", "why", "with",
}


def _collection_name(university_id, course_id=None):
    if course_id:
        return f"uni_{university_id}_course_{course_id}"
    return f"uni_{university_id}"


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

    # Prefer Chroma's default ONNX embedder in production to avoid heavyweight
    # Torch/CUDA dependencies while keeping local sentence-level retrieval quality.
    try:
        _EMBEDDING_FUNCTION = embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        _EMBEDDING_FUNCTION = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    return _EMBEDDING_FUNCTION


def get_or_create_collection(university_id, course_id=None):
    """
    Each university gets its own isolated collection
    Students can ONLY access their university's collection
    """
    collection_name = _collection_name(university_id, course_id)

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


def _get_target_collections_for_indexing(university_id, course_id=None):
    """
    Index in university-wide collection always, and in course-specific
    collection when course_id is provided.
    """
    collections = OrderedDict()
    global_collection = get_or_create_collection(university_id, None)
    collections[global_collection.name] = global_collection

    if course_id:
        course_collection = get_or_create_collection(university_id, course_id)
        collections[course_collection.name] = course_collection

    return list(collections.values())


def _tokenize(text):
    tokens = re.findall(r"[a-z0-9']+", (text or "").lower())
    return [token for token in tokens if len(token) > 2 and token not in _STOPWORDS]


def _build_query_variants(query_text):
    query = " ".join((query_text or "").strip().split())
    if not query:
        return []

    tokens = _tokenize(query)
    keyword_query = " ".join(tokens[:10])

    variants = [
        query,
        f"definitions and key concepts {keyword_query}".strip(),
        f"important facts and examples {keyword_query}".strip(),
    ]

    cleaned = re.sub(r"^[Ww]hat is\s+", "", query).strip(" ?.!")
    if cleaned and cleaned.lower() != query.lower():
        variants.append(cleaned)

    deduped = []
    seen = set()
    for item in variants:
        normalized = " ".join(item.split()).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped


def _lexical_overlap_score(query_tokens, candidate_tokens):
    if not query_tokens or not candidate_tokens:
        return 0.0
    query_set = set(query_tokens)
    candidate_set = set(candidate_tokens)
    overlap = query_set.intersection(candidate_set)
    return len(overlap) / max(len(query_set), 1)


def _jaccard_similarity(tokens_a, tokens_b):
    if not tokens_a or not tokens_b:
        return 0.0
    a = set(tokens_a)
    b = set(tokens_b)
    denom = len(a.union(b))
    if not denom:
        return 0.0
    return len(a.intersection(b)) / denom


def _chunk_index_from_metadata(meta):
    try:
        return int(meta.get("chunk_index", 0))
    except (TypeError, ValueError, AttributeError):
        return 0


def _query_collection_candidates(collection, queries, candidate_pool=30, where=None):
    candidates = {}
    per_query = max(6, candidate_pool // max(len(queries), 1))

    for query in queries:
        query_kwargs = {
            "query_texts": [query],
            "n_results": per_query,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        results = collection.query(**query_kwargs)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, distance in zip(documents, metadatas, distances):
            if not doc or not meta:
                continue

            doc_id = str(meta.get("document_id", ""))
            chunk_index = str(meta.get("chunk_index", "0"))
            candidate_key = f"{doc_id}:{chunk_index}"

            candidate = candidates.get(candidate_key)
            if candidate is None or (
                distance is not None
                and (
                    candidate.get("distance") is None
                    or distance < candidate.get("distance")
                )
            ):
                candidates[candidate_key] = {
                    "content": doc,
                    "metadata": meta,
                    "distance": distance,
                }

    return list(candidates.values())


def _rank_and_diversify_candidates(candidates, query_text, n_results):
    if not candidates:
        return []

    query_tokens = _tokenize(query_text)
    scored = []

    for candidate in candidates:
        content = candidate["content"]
        meta = candidate["metadata"]
        distance = candidate.get("distance")

        content_tokens = _tokenize(content)
        semantic_score = 0.0
        if distance is not None:
            semantic_score = 1.0 / (1.0 + max(distance, 0.0))

        lexical_score = _lexical_overlap_score(query_tokens, content_tokens)
        title_tokens = _tokenize(meta.get("document_title", ""))
        title_bonus = 0.06 if set(query_tokens).intersection(title_tokens) else 0.0

        rank_score = (0.72 * semantic_score) + (0.28 * lexical_score) + title_bonus

        scored.append({
            **candidate,
            "semantic_score": semantic_score,
            "lexical_score": lexical_score,
            "rank_score": rank_score,
            "chunk_index_int": _chunk_index_from_metadata(meta),
            "section_bucket": _chunk_index_from_metadata(meta) // 4,
            "tokens": content_tokens,
        })

    ranked = sorted(scored, key=lambda item: item["rank_score"], reverse=True)
    selected = []
    selected_sections = defaultdict(set)
    remaining = ranked[:]

    while remaining and len(selected) < n_results:
        best_item = None
        best_score = float("-inf")

        for item in remaining:
            doc_id = str(item["metadata"].get("document_id", ""))
            redundancy = 0.0
            proximity_penalty = 0.0

            for selected_item in selected:
                redundancy = max(
                    redundancy,
                    _jaccard_similarity(item["tokens"], selected_item["tokens"]),
                )
                if doc_id == str(selected_item["metadata"].get("document_id", "")):
                    if abs(item["chunk_index_int"] - selected_item["chunk_index_int"]) <= 1:
                        proximity_penalty = max(proximity_penalty, 0.05)

            section_bonus = 0.08 if item["section_bucket"] not in selected_sections[doc_id] else 0.0
            mmr_score = (0.84 * item["rank_score"]) - (0.16 * redundancy) + section_bonus - proximity_penalty

            if mmr_score > best_score:
                best_score = mmr_score
                best_item = item

        if best_item is None:
            break

        selected.append(best_item)
        doc_id = str(best_item["metadata"].get("document_id", ""))
        selected_sections[doc_id].add(best_item["section_bucket"])
        remaining = [item for item in remaining if item is not best_item]

    return selected


def _format_results(candidates, n_results):
    if not candidates:
        return []

    max_distance = getattr(settings, "RAG_MAX_DISTANCE", 1.2)
    min_keep = max(2, min(n_results, 4))

    in_threshold = [
        c for c in candidates
        if c.get("distance") is None or c.get("distance") <= max_distance
    ]

    if len(in_threshold) < min_keep:
        in_threshold = candidates[:min_keep]

    formatted = []
    for candidate in in_threshold[:n_results]:
        meta = candidate["metadata"]
        formatted.append({
            "content": candidate["content"],
            "source": meta.get("document_title", "Unknown"),
            "chunk": meta.get("chunk_index", "0"),
            "distance": candidate.get("distance"),
            "rank_score": round(candidate.get("rank_score", 0.0), 4),
            "semantic_score": round(candidate.get("semantic_score", 0.0), 4),
            "lexical_score": round(candidate.get("lexical_score", 0.0), 4),
            "document_id": meta.get("document_id"),
        })

    return formatted


def _merge_results(primary, secondary, n_results):
    merged = OrderedDict()
    for item in (primary or []) + (secondary or []):
        key = f"{item.get('document_id', '')}:{item.get('chunk', '0')}"
        existing = merged.get(key)
        if existing is None or item.get("rank_score", 0.0) > existing.get("rank_score", 0.0):
            merged[key] = item

    combined = list(merged.values())
    combined.sort(key=lambda x: x.get("rank_score", 0.0), reverse=True)
    return combined[:n_results]


def _query_collection_object(collection, query_text, n_results=5, document_id=None):
    query_variants = _build_query_variants(query_text)

    where = {"document_id": str(document_id)} if document_id is not None else None
    candidate_pool = max(24, n_results * 8)
    candidates = _query_collection_candidates(
        collection=collection,
        queries=query_variants,
        candidate_pool=candidate_pool,
        where=where,
    )
    ranked = _rank_and_diversify_candidates(candidates, query_text=query_text, n_results=max(6, n_results * 2))
    return _format_results(ranked, n_results=n_results)


def _query_collection(university_id, query_text, course_id=None, n_results=5, document_id=None):
    collection = get_or_create_collection(university_id, course_id)
    return _query_collection_object(
        collection=collection,
        query_text=query_text,
        n_results=n_results,
        document_id=document_id,
    )


def _query_collection_by_name(collection_name, query_text, n_results=5, document_id=None):
    client = get_chroma_client()
    ef = get_embedding_function()
    try:
        collection = client.get_collection(name=collection_name, embedding_function=ef)
    except Exception:
        return []

    return _query_collection_object(
        collection=collection,
        query_text=query_text,
        n_results=n_results,
        document_id=document_id,
    )


def _list_course_collection_names(university_id):
    client = get_chroma_client()
    prefix = f"uni_{university_id}_course_"
    names = []
    for collection in client.list_collections():
        name = getattr(collection, "name", collection)
        if isinstance(name, str) and name.startswith(prefix):
            names.append(name)
    return names


def add_document_to_rag(document, chunks, university_id, course_id=None):
    """
    Professor uploads doc → stored in university's isolated RAG collection
    """
    texts = []
    ids = []
    metadatas = []
    document_course_id = course_id or getattr(document, "course_id", None)

    for chunk in chunks:
        texts.append(chunk.content)
        ids.append(f"doc_{document.id}_chunk_{chunk.chunk_index}")
        metadata = {
            "document_id": str(document.id),
            "document_title": document.title,
            "chunk_index": str(chunk.chunk_index),
            "university_id": str(university_id),
        }
        if document_course_id:
            metadata["course_id"] = str(document_course_id)
        metadatas.append(metadata)

    if texts:
        collections = _get_target_collections_for_indexing(university_id, course_id=document_course_id)
        for collection in collections:
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
        primary_results = _query_collection(
            university_id=university_id,
            query_text=query_text,
            course_id=course_id,
            n_results=n_results,
            document_id=document_id,
        )

        if course_id and len(primary_results) < max(2, n_results // 2):
            # Fallback to university-wide collection for cross-course materials.
            fallback_results = _query_collection(
                university_id=university_id,
                query_text=query_text,
                course_id=None,
                n_results=n_results,
                document_id=document_id,
            )
            return _merge_results(primary_results, fallback_results, n_results=n_results)

        if not course_id and len(primary_results) < n_results:
            # Backward compatibility: older data may exist only in course collections.
            course_collection_names = _list_course_collection_names(university_id)
            additional = []
            per_collection = max(2, n_results // 2)
            for collection_name in course_collection_names[:8]:
                additional.extend(
                    _query_collection_by_name(
                        collection_name=collection_name,
                        query_text=query_text,
                        n_results=per_collection,
                        document_id=document_id,
                    )
                )
            if additional:
                return _merge_results(primary_results, additional, n_results=n_results)

        return primary_results

    except Exception as e:
        print(f"RAG query error: {e}")
        return []


def _get_collections_for_delete(university_id, course_id=None):
    client = get_chroma_client()
    ef = get_embedding_function()
    prefix = f"uni_{university_id}"

    names = []
    if course_id:
        names = [_collection_name(university_id), _collection_name(university_id, course_id)]
    else:
        listed = client.list_collections()
        for collection in listed:
            name = getattr(collection, "name", collection)
            if isinstance(name, str) and (name == prefix or name.startswith(f"{prefix}_course_")):
                names.append(name)

    deduped_names = []
    seen = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        deduped_names.append(name)

    collections = []
    for name in deduped_names:
        if not name:
            continue
        try:
            collections.append(client.get_collection(name=name, embedding_function=ef))
        except Exception:
            continue
    return collections


def delete_document_from_rag(document_id, university_id, course_id=None):
    """Remove a document from RAG when deleted"""
    try:
        collections = _get_collections_for_delete(university_id, course_id=course_id)
        if not collections:
            return True

        for collection in collections:
            collection.delete(where={"document_id": str(document_id)})
        return True
    except Exception as e:
        print(f"RAG delete error: {e}")
        return False
