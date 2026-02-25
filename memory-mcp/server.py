"""Memory MCP Server -- persistent knowledge base for Claude Code.

Provides 7 tools for saving, searching, updating, and managing memories
across conversations. Uses sqlite-vec for vector search and FTS5 for
keyword search, with embeddings from LM Studio.
"""

from __future__ import annotations

import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

# Add our directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import MemoryDB
from embeddings import EmbeddingClient
from hybrid_search import hybrid_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory-mcp")

# Configuration from environment
GLOBAL_DB_PATH = os.environ.get(
    "MEMORY_DB_GLOBAL",
    os.path.expanduser("~/.claude/memory/memory.db"),
)
LMS_URL = os.environ.get("LMS_EMBEDDING_URL", "http://localhost:1234/v1/embeddings")
LMS_MODEL = os.environ.get("LMS_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")

# Initialize
mcp = FastMCP("memory", instructions="Persistent knowledge base for Claude Code. Use memory_save to store decisions, patterns, errors, and learnings. Use memory_search for semantic retrieval. Use memory_context to load relevant context for a task.")
db = MemoryDB(GLOBAL_DB_PATH)
embedder = EmbeddingClient(url=LMS_URL, model=LMS_MODEL)


@mcp.tool()
async def memory_save(
    content: str,
    category: str,
    summary: str = "",
    tags: list[str] | None = None,
    project: str | None = None,
    importance: int = 5,
) -> str:
    """Save a piece of knowledge to the memory system.

    Categories: decision, pattern, error, solution, learning, context, rule, persona.
    Importance: 1-10 scale (10 = critical rules, 1 = temporary notes).
    """
    tags = tags or []

    # Generate embedding
    embedding = await embedder.embed(content)

    mem_id = db.save(
        content=content,
        category=category,
        summary=summary or content[:100],
        tags=tags,
        project=project,
        importance=importance,
        source="manual",
        embedding=embedding,
    )

    embed_status = "with embedding" if embedding else "without embedding (LM Studio unavailable)"
    return json.dumps({
        "status": "saved",
        "id": mem_id,
        "category": category,
        "importance": importance,
        "embedding": embed_status,
    })


@mcp.tool()
async def memory_search(
    query: str,
    category: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
    limit: int = 5,
    min_importance: int | None = None,
) -> str:
    """Search the knowledge base using hybrid semantic + keyword search.

    Uses 70% vector similarity + 30% BM25 keyword relevance for ranking.
    """
    # Generate query embedding
    query_embedding = await embedder.embed(query)

    results = hybrid_search(
        db=db,
        query=query,
        query_embedding=query_embedding,
        limit=limit,
        category=category,
        project=project,
        tags=tags or None,
        min_importance=min_importance,
    )

    return json.dumps({
        "query": query,
        "count": len(results),
        "search_mode": "hybrid" if query_embedding else "keyword-only",
        "results": results,
    })


@mcp.tool()
async def memory_update(
    id: str,
    content: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    importance: int | None = None,
    category: str | None = None,
) -> str:
    """Update an existing memory. Re-embeds content if text changes."""
    embedding = None
    if content is not None:
        embedding = await embedder.embed(content)

    success = db.update(
        mem_id=id,
        content=content,
        summary=summary,
        tags=tags,
        importance=importance,
        category=category,
        embedding=embedding,
    )

    if success:
        return json.dumps({"status": "updated", "id": id})
    else:
        return json.dumps({"status": "not_found", "id": id})


@mcp.tool()
async def memory_delete(id: str, confirm: bool = False) -> str:
    """Permanently delete a memory. Set confirm=True to proceed."""
    if not confirm:
        return json.dumps({"status": "rejected", "reason": "confirm must be True"})

    success = db.delete(id)
    if success:
        return json.dumps({"status": "deleted", "id": id})
    else:
        return json.dumps({"status": "not_found", "id": id})


@mcp.tool()
async def memory_list(
    category: str | None = None,
    project: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
) -> str:
    """List memories with optional filters. Returns compact summaries."""
    results = db.list_memories(
        category=category,
        project=project,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Compact format: summary or first 100 chars of content
    compact = [
        {
            "id": r["id"],
            "category": r["category"],
            "summary": r["summary"] or r["content"][:100],
            "importance": r["importance"],
            "project": r["project"],
            "updated_at": r["updated_at"],
        }
        for r in results
    ]

    return json.dumps({"count": len(compact), "results": compact})


@mcp.tool()
async def memory_get(id: str) -> str:
    """Get full details of a specific memory by ID. Increments access count."""
    memory = db.get(id)
    if memory is None:
        return json.dumps({"status": "not_found", "id": id})
    return json.dumps(memory)


@mcp.tool()
async def memory_context(
    task_description: str,
    project: str | None = None,
    include_rules: bool = True,
    max_tokens: int = 2000,
) -> str:
    """Load relevant context for the current task.

    Searches rules (always), project-specific patterns, recent errors/solutions,
    and relevant decisions. Returns a structured context block.
    """
    context_parts = []
    token_budget = max_tokens

    # Always load rules first
    if include_rules:
        rules = db.list_memories(category="rule", sort_by="importance", sort_order="desc", limit=20)
        if rules:
            rules_text = "\n".join(f"- [{r['importance']}/10] {r['summary'] or r['content'][:100]}" for r in rules)
            context_parts.append(f"## Rules\n{rules_text}")
            token_budget -= len(rules_text) // 4  # Rough token estimate

    # Search for task-relevant context
    if token_budget > 200:
        query_embedding = await embedder.embed(task_description)
        relevant = hybrid_search(
            db=db,
            query=task_description,
            query_embedding=query_embedding,
            limit=10,
            project=project,
        )

        if relevant:
            # Filter out rules (already included)
            relevant = [r for r in relevant if r["category"] != "rule"]
            relevant_text = "\n".join(
                f"- [{r['category']}] {r['summary'] or r['content'][:150]}"
                for r in relevant[:8]
            )
            context_parts.append(f"## Relevant Context\n{relevant_text}")

    # Load project-specific context
    if project and token_budget > 100:
        proj_context = db.list_memories(
            category="context", project=project, limit=5
        )
        if proj_context:
            proj_text = "\n".join(
                f"- {r['summary'] or r['content'][:100]}" for r in proj_context
            )
            context_parts.append(f"## Project Context\n{proj_text}")

    full_context = "\n\n".join(context_parts)
    return json.dumps({
        "task": task_description,
        "context": full_context,
        "rules_loaded": include_rules,
        "project": project,
    })


def main():
    """Run the MCP server."""
    if "--health-check" in sys.argv:
        print("Memory MCP server OK")
        print(f"Database: {GLOBAL_DB_PATH}")
        print(f"Embedding URL: {LMS_URL}")
        sys.exit(0)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
