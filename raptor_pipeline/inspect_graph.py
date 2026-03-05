"""Utility script to browse Knowledge Graph in Neo4j and link back to Qdrant text."""
from __future__ import annotations

import hydra
from omegaconf import DictConfig
from qdrant_client import QdrantClient
from qdrant_client.http import models
from neo4j import GraphDatabase

def get_chunk_text(q_client: QdrantClient, collection: str, chunk_id: str) -> str:
    """Fetch text for a specific chunk_id from Qdrant."""
    # We store node_id in payload, and chunk_id is used for node_id during extraction
    points, _ = q_client.scroll(
        collection_name=collection,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="node_id",
                    match=models.MatchValue(value=chunk_id),
                )
            ]
        ),
        limit=1,
        with_payload=True,
    )
    if points and points[0].payload:
        return points[0].payload.get("text", "[No text found]")
    return "[Chunk not found in Qdrant]"

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    # 1. Connect to Neo4j
    n_cfg = cfg.stores.neo4j
    driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))
    
    # 2. Connect to Qdrant
    q_cfg = cfg.stores.qdrant
    q_client = QdrantClient(host=q_cfg.host, port=q_cfg.port)
    q_collection = q_cfg.collection_name

    keyword_to_inspect = cfg.get("word", None)

    with driver.session(database=n_cfg.database) as session:
        if not keyword_to_inspect:
            # Mode A: List keywords
            print("\nAvailable Keywords in Neo4j:")
            print("=" * 60)
            result = session.run("MATCH (k:Keyword) RETURN k.word AS word, k.category AS category ORDER BY word")
            keywords = list(result)
            if not keywords:
                print("No keywords found in Neo4j.")
            for kw in keywords:
                print(f"- {kw['word']} ({kw['category']})")
            print("=" * 60)
            print("\nTip: Run with 'word=\"YOUR_KEYWORD\"' to see relationships and source text.")
        
        else:
            # Mode B: Inspect specific keyword
            print(f"\nInspecting Keyword: '{keyword_to_inspect}'")
            print("=" * 60)
            
            # 1. Direct relationships
            result = session.run(
                """
                MATCH (s:Keyword {word: $word})-[r:RELATED_TO]->(o:Keyword)
                RETURN s.word AS subject, r.predicate AS predicate, o.word AS object, r.chunk_ids AS chunk_ids
                UNION
                MATCH (s:Keyword)-[r:RELATED_TO]->(o:Keyword {word: $word})
                RETURN s.word AS subject, r.predicate AS predicate, o.word AS object, r.chunk_ids AS chunk_ids
                """,
                word=keyword_to_inspect
            )
            
            relations = list(result)
            if not relations:
                print(f"No relations found for '{keyword_to_inspect}'.")
            else:
                print(f"Found {len(relations)} relations:")
                processed_chunks = set()
                
                for rel in relations:
                    print(f"\n[RELATION] ({rel['subject']}) --[{rel['predicate']}]--> ({rel['object']})")
                    c_ids = rel.get('chunk_ids', []) or []
                    if isinstance(c_ids, str): c_ids = [c_ids]
                    for c_id in c_ids:
                        if c_id and c_id not in processed_chunks:
                            print(f"Source Chunk ID: {c_id}")
                            text = get_chunk_text(q_client, q_collection, c_id)
                            # Indented text
                            indented_text = "\n".join(["    | " + line for line in text.split("\n")])
                            print(f"Source Text:\n{indented_text}")
                            processed_chunks.add(c_id)
            
            # 2. Entities related via HAS_KEYWORD (what articles mention this?)
            result = session.run(
                """
                MATCH (a:Article)-[r:HAS_KEYWORD]->(k:Keyword {word: $word})
                RETURN a.id AS article_id, r.chunk_ids AS chunk_ids
                """,
                word=keyword_to_inspect
            )
            articles = list(result)
            if articles:
                print("\nArticles mentioning this keyword:")
                for art in articles:
                    c_ids = art.get('chunk_ids', []) or []
                    if isinstance(c_ids, str): c_ids = [c_ids]
                    print(f"- Article: {art['article_id']} (Chunks: {', '.join(c_ids)})")

    driver.close()

if __name__ == "__main__":
    main()
