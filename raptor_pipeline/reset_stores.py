"""Utility script to manage data in Qdrant and Neo4j.

Usage:
    # List all articles
    uv run python -m raptor_pipeline.reset_stores mode=list

    # Delete specific article by ID
    uv run python -m raptor_pipeline.reset_stores mode=delete article_id="my_article_id"

    # Delete ALL data (clean slate)
    uv run python -m raptor_pipeline.reset_stores mode=reset
"""
from __future__ import annotations

import hydra
from omegaconf import DictConfig
from qdrant_client import QdrantClient
from qdrant_client.http import models
from neo4j import GraphDatabase


def _connect(cfg: DictConfig):
    """Create Qdrant and Neo4j connections."""
    q_cfg = cfg.stores.qdrant
    q_client = QdrantClient(host=q_cfg.host, port=q_cfg.port)
    collection = q_cfg.collection_name

    n_cfg = cfg.stores.neo4j
    driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))

    return q_client, collection, driver, n_cfg.database


# ── List ──────────────────────────────────────────────────────
def list_articles(cfg: DictConfig) -> None:
    """Print all article IDs from Neo4j with metadata."""
    _, _, driver, db = _connect(cfg)

    with driver.session(database=db) as session:
        result = session.run(
            """
            MATCH (a:Article)
            OPTIONAL MATCH (a)-[:HAS_KEYWORD]->(k:Keyword)
            OPTIONAL MATCH (a)-[ref:REFERENCES]->()
            RETURN a.id AS id,
                   a.article_name AS name,
                   a.version AS version,
                   count(DISTINCT k) AS keywords,
                   count(DISTINCT ref) AS refs
            ORDER BY a.id
            """
        )
        articles = list(result)

    driver.close()

    if not articles:
        print("No articles found in Neo4j.")
        return

    print(f"\n{'='*80}")
    print(f"{'ID':<45} {'Name':<20} {'Ver':<16} {'KW':>4} {'Ref':>4}")
    print(f"{'='*80}")
    for art in articles:
        aid = art["id"] or "?"
        name = (art["name"] or "")[:20]
        ver = art["version"] or "-"
        kw = art["keywords"]
        refs = art["refs"]
        print(f"{aid:<45} {name:<20} {ver:<16} {kw:>4} {refs:>4}")
    print(f"{'='*80}")
    print(f"Total: {len(articles)} articles")
    print("\nTip: uv run python -m raptor_pipeline.reset_stores mode=delete article_id=\"ID\"")


# ── Delete one article ────────────────────────────────────────
def delete_article(cfg: DictConfig, article_id: str) -> None:
    """Delete a specific article and all its data from both stores."""
    q_client, collection, driver, db = _connect(cfg)

    print(f"\nDeleting article '{article_id}'...")

    # 1. Neo4j: delete article, its keywords (if orphan), relations, references
    with driver.session(database=db) as session:
        # Delete relations where keywords belong only to this article
        summary = session.run(
            """
            MATCH (a:Article {id: $id})-[:HAS_KEYWORD]->(k:Keyword)
            OPTIONAL MATCH (k)-[rel:RELATED_TO]-()
            WHERE NOT exists {
                MATCH (other:Article)-[:HAS_KEYWORD]->(k)
                WHERE other.id <> $id
            }
            DELETE rel
            DETACH DELETE k
            RETURN count(k) AS deleted_keywords
            """,
            id=article_id,
        ).single()
        kw_count = summary["deleted_keywords"] if summary else 0

        # Delete REFERENCES from this article
        ref_summary = session.run(
            """
            MATCH (a:Article {id: $id})-[r:REFERENCES]->()
            DELETE r
            RETURN count(r) AS deleted_refs
            """,
            id=article_id,
        ).single()
        ref_count = ref_summary["deleted_refs"] if ref_summary else 0

        # Delete REFERENCES to this article
        ref_in_summary = session.run(
            """
            MATCH ()-[r:REFERENCES]->(a:Article {id: $id})
            DELETE r
            RETURN count(r) AS deleted_refs
            """,
            id=article_id,
        ).single()
        ref_in_count = ref_in_summary["deleted_refs"] if ref_in_summary else 0

        # Delete article node itself
        session.run("MATCH (a:Article {id: $id}) DETACH DELETE a", id=article_id)

    driver.close()
    print(f"  + Neo4j: {kw_count} keywords, {ref_count + ref_in_count} references deleted")

    # 2. Qdrant: delete points with this article_id
    try:
        q_client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="article_id",
                            match=models.MatchValue(value=article_id),
                        )
                    ]
                )
            ),
        )
        print(f"  + Qdrant: points for '{article_id}' deleted")
    except Exception as e:
        print(f"  × Qdrant error: {e}")

    print(f"\n✓ Article '{article_id}' removed from all stores.")


# ── Reset all ─────────────────────────────────────────────────
def reset_all(cfg: DictConfig) -> None:
    """Wipe ALL data from both stores."""
    q_client, collection, driver, db = _connect(cfg)

    # 1. Qdrant
    print(f"Cleaning Qdrant collection '{collection}'...")
    try:
        q_client.delete_collection(collection_name=collection)
        print("  + Qdrant collection deleted.")
    except Exception as e:
        print(f"  × Qdrant error: {e}")

    # 2. Neo4j
    print(f"Cleaning Neo4j database '{db}'...")
    try:
        with driver.session(database=db) as session:
            summary = session.run("MATCH (n) DETACH DELETE n").consume()
            print(f"  + Neo4j: {summary.counters.nodes_deleted} nodes deleted.")
    except Exception as e:
        print(f"  × Neo4j error: {e}")

    driver.close()
    print("\n✓ Reset complete. Clean slate.")


# ── Entry point ──────────────────────────────────────────────
@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    mode = cfg.get("mode", "list")
    article_id = cfg.get("article_id", None)

    if mode == "list":
        list_articles(cfg)
    elif mode == "delete":
        if not article_id:
            print("Error: article_id is required for delete mode.")
            print("Usage: uv run python -m raptor_pipeline.reset_stores mode=delete article_id=\"ID\"")
            return
        delete_article(cfg, article_id)
    elif mode == "reset":
        reset_all(cfg)
    else:
        print(f"Unknown mode '{mode}'. Use: list, delete, reset")


if __name__ == "__main__":
    main()
