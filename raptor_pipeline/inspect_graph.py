"""Utility script to browse Knowledge Graph in Neo4j and link back to Qdrant text."""
from __future__ import annotations

import sys
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


def _fix_cyrillic_args():
    """Fix Hydra LexerNoViableAltException for Cyrillic values.

    Hydra's OmegaConf lexer can't handle non-ASCII characters in
    unquoted CLI values.  We wrap such values in single quotes so
    OmegaConf treats them as plain strings.

    Example:
        word=оптимизация  →  word='оптимизация'
    """
    fixed = []
    for arg in sys.argv[1:]:
        if "=" in arg and not arg.startswith("--"):
            key, value = arg.split("=", 1)
            # If value has non-ASCII chars and is not already quoted
            has_non_ascii = any(ord(c) > 127 for c in value)
            already_quoted = (
                (value.startswith("'") and value.endswith("'"))
                or (value.startswith('"') and value.endswith('"'))
            )
            if has_non_ascii and not already_quoted:
                arg = f"{key}='{value}'"
        fixed.append(arg)
    sys.argv[1:] = fixed


# Apply the fix BEFORE Hydra parses args
_fix_cyrillic_args()


def main(cfg: DictConfig, article_id: str | None = None, min_confidence: float | None = None) -> None:
    """Core inspect-graph logic, callable from Click or standalone."""
    # 1. Connect to Neo4j
    n_cfg = cfg.stores.neo4j
    driver = GraphDatabase.driver(n_cfg.uri, auth=(n_cfg.user, n_cfg.password))
    
    # 2. Connect to Qdrant
    q_cfg = cfg.stores.qdrant
    q_client = QdrantClient(host=q_cfg.host, port=q_cfg.port)
    q_collection = q_cfg.collection_name

    keyword_to_inspect = cfg.get("word", None)
    # article_id can come from function arg or config
    filter_article = article_id or cfg.get("article_id", None)

    with driver.session(database=n_cfg.database) as session:
        if not keyword_to_inspect:
            if filter_article:
                # Mode A2: List keywords for a specific article (with confidence)
                conf_label = f" (confidence ≥ {min_confidence})" if min_confidence else ""
                print(f"\nKeywords for Article '{filter_article}'{conf_label}:")
                print("=" * 60)
                result = session.run(
                    """
                    MATCH (a:Article {id: $article_id})-[r:HAS_KEYWORD]->(k:Keyword)
                    RETURN k.word AS word, k.category AS category,
                           r.confidence AS confidence,
                           k.original_words AS original_words,
                           r.chunk_ids AS chunk_ids
                    ORDER BY r.confidence DESC, word
                    """,
                    article_id=filter_article,
                )
                all_keywords = list(result)
                # Apply min_confidence filter
                if min_confidence is not None:
                    keywords = [kw for kw in all_keywords if (kw.get('confidence') or 0) >= min_confidence]
                else:
                    keywords = all_keywords
                if not all_keywords:
                    print(f"No keywords found for article '{filter_article}'.")
                    # Debug: check if article exists
                    art = session.run(
                        "MATCH (a:Article {id: $id}) RETURN a.id AS id, a.article_name AS name",
                        id=filter_article,
                    ).single()
                    if art:
                        print(f"  Article exists: {art['id']} ({art.get('name', '?')})")
                        raw_count = session.run(
                            "MATCH (a:Article {id: $id})-[r:HAS_KEYWORD]->(k) RETURN count(r) AS cnt",
                            id=filter_article,
                        ).single()
                        print(f"  Total HAS_KEYWORD edges: {raw_count['cnt'] if raw_count else 0}")
                    else:
                        print(f"  Article '{filter_article}' NOT FOUND in Neo4j.")
                        similar = session.run(
                            "MATCH (a:Article) WHERE a.id CONTAINS $partial OR a.article_name CONTAINS $partial "
                            "RETURN a.id AS id, a.article_name AS name LIMIT 5",
                            partial=filter_article,
                        ).data()
                        if similar:
                            print(f"  Similar articles: {similar}")
                elif not keywords:
                    print(f"No keywords with confidence ≥ {min_confidence} (total: {len(all_keywords)})")
                else:
                    for kw in keywords:
                        conf = kw.get('confidence')
                        conf_str = f"  conf={conf:.2f}" if conf is not None else "  conf=NULL"
                        orig = kw.get('original_words') or []
                        orig_str = f"  ← merged: [{', '.join(orig)}]" if orig else ""
                        chunks = kw.get('chunk_ids') or []
                        chunks_str = f"  [{len(chunks)} chunks]" if chunks else ""
                        print(f"- {kw['word']} ({kw['category']}){conf_str}{chunks_str}{orig_str}")
                print("=" * 60)
                shown = len(keywords)
                total = len(all_keywords)
                if min_confidence is not None and total != shown:
                    print(f"Shown: {shown}/{total} keywords (confidence ≥ {min_confidence})")
                else:
                    print(f"Total: {total} keywords")
                # Show confidence distribution
                if all_keywords:
                    confs = [kw.get('confidence') or 0 for kw in all_keywords]
                    high = sum(1 for c in confs if c >= 0.8)
                    med = sum(1 for c in confs if 0.5 <= c < 0.8)
                    low = sum(1 for c in confs if c < 0.5)
                    print(f"  Confidence: ≥0.8: {high}, 0.5-0.8: {med}, <0.5: {low}")
            else:
                # Mode A1: List all keywords globally
                print("\nAvailable Keywords in Neo4j:")
                print("=" * 60)
                result = session.run(
                    """
                    MATCH (k:Keyword)
                    OPTIONAL MATCH ()-[r:HAS_KEYWORD]->(k)
                    RETURN k.word AS word, k.category AS category,
                           k.original_words AS original_words,
                           max(r.confidence) AS max_confidence,
                           count(r) AS article_count
                    ORDER BY word
                    """
                )
                keywords = list(result)
                if not keywords:
                    print("No keywords found in Neo4j.")
                for kw in keywords:
                    conf = kw.get('max_confidence')
                    conf_str = f"  conf={conf:.2f}" if conf is not None else ""
                    art_count = kw.get('article_count', 0)
                    art_str = f"  [{art_count} articles]" if art_count else ""
                    orig = kw.get('original_words') or []
                    orig_str = f"  ← merged: [{', '.join(orig)}]" if orig else ""
                    print(f"- {kw['word']} ({kw['category']}){conf_str}{art_str}{orig_str}")
                print("=" * 60)
                print(f"Total: {len(keywords)} keywords")
            print("\nTip: Run with '--word YOUR_KEYWORD' to see relationships and source text.")
            print("     Use '--article-id ID' to filter by article.")
        
        else:
            # Mode B: Inspect specific keyword
            print(f"\nInspecting Keyword: '{keyword_to_inspect}'")
            print("=" * 60)

            # 0. Show keyword info + original_words
            kw_info = session.run(
                "MATCH (k:Keyword {word: $word}) RETURN k.category AS category, k.original_words AS original_words",
                word=keyword_to_inspect,
            )
            kw_record = kw_info.single()
            if kw_record:
                print(f"Category: {kw_record['category']}")
                orig = kw_record.get('original_words') or []
                if orig:
                    print(f"Merged from: {orig}")
                else:
                    print("Merged from: (not a merged keyword)")
            print()

            # 1. Relations — grouped by source chunk
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
                print(f"Found {len(relations)} relations:\n")

                # Group relations by chunk_id
                chunk_to_rels: dict[str, list[dict]] = {}
                for rel in relations:
                    c_ids = rel.get('chunk_ids', []) or []
                    if isinstance(c_ids, str):
                        c_ids = [c_ids]
                    if not c_ids:
                        c_ids = ["(no chunk)"]
                    for c_id in c_ids:
                        chunk_to_rels.setdefault(c_id, []).append(dict(rel))
                
                processed_chunks = set()
                for c_id, rels_in_chunk in chunk_to_rels.items():
                    print(f"{'─' * 50}")
                    print(f"📦 Source Chunk: {c_id}")
                    print(f"{'─' * 50}")
                    for rel in rels_in_chunk:
                        print(f"  ({rel['subject']}) --[{rel['predicate']}]--> ({rel['object']})")
                    
                    # Show chunk text once per group
                    if c_id and c_id != "(no chunk)" and c_id not in processed_chunks:
                        text = get_chunk_text(q_client, q_collection, c_id)
                        indented_text = "\n".join(["    | " + line for line in text.split("\n")])
                        print(f"\n  Source Text:\n{indented_text}")
                        processed_chunks.add(c_id)
                    print()
            
            # 2. Articles mentioning this keyword via HAS_KEYWORD
            result = session.run(
                """
                MATCH (a:Article)-[r:HAS_KEYWORD]->(k:Keyword {word: $word})
                RETURN a.id AS article_id, a.article_name AS article_name,
                       r.confidence AS confidence, r.chunk_ids AS chunk_ids
                """,
                word=keyword_to_inspect
            )
            articles = list(result)
            if articles:
                print("\nArticles mentioning this keyword:")
                for art in articles:
                    c_ids = art.get('chunk_ids', []) or []
                    if isinstance(c_ids, str): c_ids = [c_ids]
                    conf = art.get('confidence')
                    conf_str = f" conf={conf:.2f}" if conf is not None else " conf=NULL"
                    name = art.get('article_name') or ''
                    name_str = f" ({name})" if name else ''
                    print(f"- Article: {art['article_id']}{name_str}{conf_str} (Chunks: {', '.join(c_ids)})")

            # 3. Cross-article references (REFERENCES edges) involving this keyword/article
            result = session.run(
                """
                MATCH (src:Article)-[r:REFERENCES]->(tgt:Article)
                WHERE src.id = $word OR tgt.id = $word
                   OR src.article_name = $word OR tgt.article_name = $word
                RETURN src.id AS source, tgt.id AS target,
                       r.display AS display, r.section AS section,
                       r.chunk_ids AS chunk_ids
                """,
                word=keyword_to_inspect,
            )
            refs = list(result)
            if refs:
                print(f"\nCross-article references involving '{keyword_to_inspect}':")
                for ref in refs:
                    c_ids = ref.get('chunk_ids', []) or []
                    if isinstance(c_ids, str):
                        c_ids = [c_ids]
                    chunk_str = f" (from chunks: {', '.join(c_ids)})" if c_ids else ""
                    section_str = f"#{ref['section']}" if ref.get('section') else ""
                    print(f"  [{ref['source']}] → [{ref['target']}{section_str}]"
                          f" display='{ref.get('display', '')}'{chunk_str}")
                    # Show source text for link chunks
                    for c_id in c_ids:
                        if c_id:
                            text = get_chunk_text(q_client, q_collection, c_id)
                            indented = "\n".join(["      | " + line for line in text.split("\n")])
                            print(f"    Source chunk ({c_id}):\n{indented}")

    driver.close()

@hydra.main(config_path="conf", config_name="config", version_base=None)
def _hydra_main(cfg: DictConfig) -> None:
    main(cfg)

if __name__ == "__main__":
    _hydra_main()
