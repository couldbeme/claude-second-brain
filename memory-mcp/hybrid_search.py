"""Hybrid search combining vector similarity and BM25 keyword search."""

from __future__ import annotations

from typing import Optional

from db import MemoryDB


# Default weights: 70% vector + 30% keyword
DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_KEYWORD_WEIGHT = 0.3


def hybrid_search(
    db: MemoryDB,
    query: str,
    query_embedding: Optional[list[float]],
    limit: int = 5,
    category: Optional[str] = None,
    project: Optional[str] = None,
    tags: Optional[list[str]] = None,
    min_importance: Optional[int] = None,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
) -> list[dict]:
    """
    Perform hybrid search combining vector similarity and BM25 keyword search.

    If embeddings are not available, falls back to keyword-only search.
    Results are merged and ranked by combined score.
    """
    # Gather results from both search methods
    vector_results = {}
    keyword_results = {}

    # Vector search (if embedding available)
    if query_embedding is not None:
        vec_raw = db.vector_search(query_embedding, limit=limit * 2)
        # Normalize distances to 0-1 similarity scores
        if vec_raw:
            max_dist = max(r["distance"] for r in vec_raw) or 1.0
            for r in vec_raw:
                similarity = 1.0 - (r["distance"] / (max_dist + 1e-6))
                vector_results[r["id"]] = {**r, "vector_score": similarity}

    # Keyword search
    kw_raw = db.keyword_search(query, limit=limit * 2)
    if kw_raw:
        # BM25 scores are negative (lower = better), normalize to 0-1
        min_score = min(r["score"] for r in kw_raw) or -1.0
        for r in kw_raw:
            relevance = r["score"] / (min_score - 1e-6) if min_score < 0 else 0.5
            keyword_results[r["id"]] = {**r, "keyword_score": relevance}

    # Merge results
    all_ids = set(vector_results.keys()) | set(keyword_results.keys())
    merged = []

    for mem_id in all_ids:
        vec_entry = vector_results.get(mem_id, {})
        kw_entry = keyword_results.get(mem_id, {})

        vec_score = vec_entry.get("vector_score", 0.0)
        kw_score = kw_entry.get("keyword_score", 0.0)

        # If only one source has results, use that source's weight as 1.0
        if query_embedding is None:
            combined_score = kw_score
        elif not keyword_results:
            combined_score = vec_score
        else:
            combined_score = (vector_weight * vec_score) + (keyword_weight * kw_score)

        # Boost by importance (mild: 10% max boost)
        entry = vec_entry or kw_entry
        importance = entry.get("importance", 5)
        importance_boost = 1.0 + (importance - 5) * 0.02
        combined_score *= importance_boost

        # Multiply by confidence (NULL → treat as 0.75)
        confidence = entry.get("confidence")
        if confidence is None:
            confidence = 0.75
        combined_score *= confidence

        merged.append({
            "id": mem_id,
            "content": entry.get("content", ""),
            "summary": entry.get("summary"),
            "category": entry.get("category", ""),
            "project": entry.get("project"),
            "tags": entry.get("tags", []),
            "importance": importance,
            "confidence": confidence,
            "score": round(combined_score, 4),
            "vector_score": round(vec_score, 4),
            "keyword_score": round(kw_score, 4),
        })

    # Apply filters
    if category:
        merged = [r for r in merged if r["category"] == category]
    if project:
        merged = [r for r in merged if r["project"] == project]
    if tags:
        merged = [r for r in merged if all(t in r["tags"] for t in tags)]
    if min_importance is not None:
        merged = [r for r in merged if r["importance"] >= min_importance]

    # Sort by combined score descending, take top N
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:limit]
