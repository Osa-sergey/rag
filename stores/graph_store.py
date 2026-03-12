"""Neo4j graph store for articles, keywords, relations, topics, and metadata.

Shared module — used by both raptor_pipeline and topic_modeler.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from neo4j import GraphDatabase
from omegaconf import DictConfig

from interfaces import BaseGraphStore

if TYPE_CHECKING:
    from raptor_pipeline.knowledge_graph.base import Keyword, Relation

logger = logging.getLogger(__name__)


class Neo4jGraphStore(BaseGraphStore):
    """Neo4j integration — stores knowledge graph.

    Graph schema:
      (:Article {id, title, author, reading_time, complexity, labels, tags, hubs})
      (:Keyword {word, category})
      (:Topic   {id, label, top_keywords})
      (:Article)-[:HAS_KEYWORD {confidence, chunk_id}]->(:Keyword)
      (:Keyword)-[:RELATED_TO {predicate, confidence, chunk_id}]->(:Keyword)
      (:Article)-[:BELONGS_TO_TOPIC {confidence}]->(:Topic)
      (:Article)-[:REFERENCES]->(:Article)
    """

    def __init__(self, cfg: DictConfig) -> None:
        self._driver = GraphDatabase.driver(
            cfg.get("uri", "bolt://localhost:7687"),
            auth=(cfg.get("user", "neo4j"), cfg.get("password", "raptor_password")),
        )
        self._database = cfg.get("database", "neo4j")
        logger.info(
            "Neo4jGraphStore connected (%s, db=%s)",
            cfg.get("uri"),
            self._database,
        )

    # ------------------------------------------------------------------
    def close(self) -> None:
        self._driver.close()

    # ------------------------------------------------------------------
    def ensure_indexes(self) -> None:
        """Create indexes / constraints for fast lookups."""
        queries = [
            "CREATE INDEX IF NOT EXISTS FOR (a:Article) ON (a.id)",
            "CREATE INDEX IF NOT EXISTS FOR (k:Keyword) ON (k.word)",
            "CREATE INDEX IF NOT EXISTS FOR (t:Topic) ON (t.id)",
        ]
        with self._driver.session(database=self._database) as session:
            for q in queries:
                session.run(q)
        logger.info("Neo4j indexes ensured")

    # ------------------------------------------------------------------
    # Article CRUD
    # ------------------------------------------------------------------
    def store_article(
        self,
        article_id: str,
        title: str = "",
        summary: str = "",
        article_name: str = "",
        version: str = "",
    ) -> None:
        """Create or merge an Article node."""
        with self._driver.session(database=self._database) as session:
            session.run(
                """
                MERGE (a:Article {id: $id})
                SET a.title = $title,
                    a.summary = $summary,
                    a.article_name = $article_name,
                    a.version = $version
                """,
                id=article_id,
                title=title,
                summary=summary,
                article_name=article_name,
                version=version,
            )

    # ------------------------------------------------------------------
    def store_article_metadata(
        self,
        article_id: str,
        metadata: dict,
    ) -> None:
        """Upsert article metadata (author, tags, hubs, complexity, etc.).

        Only sets fields that are present in *metadata* dict; existing
        properties not in the dict are left untouched.

        Supported keys: author, reading_time, complexity, labels, tags, hubs.
        """
        set_clauses = []
        params: dict = {"id": article_id}

        field_map = {
            "author": "a.author",
            "reading_time": "a.reading_time",
            "complexity": "a.complexity",
            "labels": "a.labels",
            "tags": "a.tags",
            "hubs": "a.hubs",
        }
        for key, prop in field_map.items():
            if key in metadata and metadata[key] is not None:
                set_clauses.append(f"{prop} = ${key}")
                params[key] = metadata[key]

        if not set_clauses:
            return

        query = f"""
        MERGE (a:Article {{id: $id}})
        SET {', '.join(set_clauses)}
        """
        with self._driver.session(database=self._database) as session:
            session.run(query, **params)

    # ------------------------------------------------------------------
    # Cross-article links
    # ------------------------------------------------------------------
    def store_links(
        self,
        source_article_id: str,
        links: list,
        version: str = "",
    ) -> None:
        """Store cross-article references from Obsidian links.

        Creates REFERENCES relationships between Article nodes.
        Target articles that don't exist yet get created as placeholders
        (they'll be enriched when actually processed later).
        """
        with self._driver.session(database=self._database) as session:
            for link in links:
                if link.link_type != "obsidian" or not link.target:
                    continue
                chunk_ids = link.source_chunk_ids if hasattr(link, 'source_chunk_ids') else []
                target_name = link.target_article_id

                # Case-insensitive lookup for existing article
                # to avoid creating duplicates with different casing.
                existing = session.run(
                    """
                    MATCH (a:Article)
                    WHERE toLower(a.article_name) = toLower($name)
                       OR toLower(a.id) = toLower($name)
                    RETURN a.id AS id
                    LIMIT 1
                    """,
                    name=target_name,
                ).single()

                target_id = existing["id"] if existing else target_name

                session.run(
                    """
                    MERGE (src:Article {id: $source_id})
                    MERGE (tgt:Article {id: $target_id})
                    ON CREATE SET tgt.article_name = $target_name
                    MERGE (src)-[r:REFERENCES]->(tgt)
                    SET r.section = $section,
                        r.display = $display,
                        r.version = $version,
                        r.raw = $raw
                    WITH r, $chunk_ids AS new_chunks
                    SET r.chunk_ids = CASE
                        WHEN r.chunk_ids IS NULL THEN new_chunks
                        ELSE [x IN (r.chunk_ids + new_chunks) WHERE x IS NOT NULL | x]
                    END
                    """,
                    source_id=source_article_id,
                    target_id=target_id,
                    target_name=target_name,
                    section=link.section,
                    display=link.display,
                    version=version,
                    raw=link.raw,
                    chunk_ids=chunk_ids,
                )

    # ------------------------------------------------------------------
    # Keywords
    # ------------------------------------------------------------------
    def store_keywords(
        self, article_id: str, keywords: list[Keyword]
    ) -> None:
        """Store keywords and link them to the article."""
        with self._driver.session(database=self._database) as session:
            for kw in keywords:
                orig_words = kw.original_words or []
                session.run(
                    """
                    MERGE (a:Article {id: $article_id})
                    MERGE (k:Keyword {word: $word})
                    SET k.category = $category
                    SET k.original_words = CASE
                        WHEN size($orig_words) > 0 THEN $orig_words
                        ELSE coalesce(k.original_words, [])
                    END
                    MERGE (a)-[r:HAS_KEYWORD]->(k)
                    ON CREATE SET r.confidence = $confidence,
                                  r.chunk_ids = [$chunk_id]
                    ON MATCH SET r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END,
                                 r.chunk_ids = CASE WHEN NOT $chunk_id IN r.chunk_ids THEN r.chunk_ids + $chunk_id ELSE r.chunk_ids END
                    """,
                    article_id=article_id,
                    word=kw.word,
                    category=kw.category,
                    confidence=kw.confidence,
                    chunk_id=kw.chunk_id,
                    orig_words=orig_words,
                )

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    def store_relations(
        self, article_id: str, relations: list[Relation]
    ) -> None:
        """Store relations as edges between Keyword nodes."""
        with self._driver.session(database=self._database) as session:
            for rel in relations:
                session.run(
                    """
                    MERGE (s:Keyword {word: $subject})
                    MERGE (o:Keyword {word: $object})
                    MERGE (s)-[r:RELATED_TO {predicate: $predicate}]->(o)
                    ON CREATE SET r.confidence = $confidence,
                                  r.chunk_ids = [$chunk_id],
                                  r.article_id = $article_id
                    ON MATCH SET r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END,
                                 r.chunk_ids = CASE WHEN NOT $chunk_id IN r.chunk_ids THEN r.chunk_ids + $chunk_id ELSE r.chunk_ids END
                    """,
                    subject=rel.subject,
                    object=rel.object,
                    predicate=rel.predicate,
                    confidence=rel.confidence,
                    chunk_id=rel.chunk_id,
                    article_id=article_id,
                )

    # ------------------------------------------------------------------
    # Topics (BERTopic)
    # ------------------------------------------------------------------
    def store_topic(
        self,
        topic_id: int,
        label: str,
        top_keywords: list[str],
    ) -> None:
        """Create or update a Topic node."""
        with self._driver.session(database=self._database) as session:
            session.run(
                """
                MERGE (t:Topic {id: $id})
                SET t.label = $label,
                    t.top_keywords = $top_keywords
                """,
                id=topic_id,
                label=label,
                top_keywords=top_keywords,
            )

    def link_article_to_topic(
        self,
        article_id: str,
        topic_id: int,
        confidence: float = 1.0,
    ) -> None:
        """Create BELONGS_TO_TOPIC relationship between Article and Topic."""
        with self._driver.session(database=self._database) as session:
            session.run(
                """
                MERGE (a:Article {id: $article_id})
                MERGE (t:Topic {id: $topic_id})
                MERGE (a)-[r:BELONGS_TO_TOPIC]->(t)
                SET r.confidence = $confidence
                """,
                article_id=article_id,
                topic_id=topic_id,
                confidence=confidence,
            )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_article_keywords(self, article_id: str) -> list[dict]:
        """Retrieve all keywords for an article."""
        with self._driver.session(database=self._database) as session:
            result = session.run(
                """
                MATCH (a:Article {id: $id})-[r:HAS_KEYWORD]->(k:Keyword)
                RETURN k.word AS word, k.category AS category,
                       r.confidence AS confidence, r.chunk_ids AS chunk_ids
                ORDER BY r.confidence DESC
                """,
                id=article_id,
            )
            return [dict(record) for record in result]

    # ------------------------------------------------------------------
    def get_keyword_relations(self, word: str) -> list[dict]:
        """Get all relations for a keyword."""
        with self._driver.session(database=self._database) as session:
            result = session.run(
                """
                MATCH (s:Keyword {word: $word})-[r:RELATED_TO]->(o:Keyword)
                RETURN s.word AS subject, r.predicate AS predicate,
                       o.word AS object, r.confidence AS confidence, r.chunk_ids AS chunk_ids
                UNION
                MATCH (s:Keyword)-[r:RELATED_TO]->(o:Keyword {word: $word})
                RETURN s.word AS subject, r.predicate AS predicate,
                       o.word AS object, r.confidence AS confidence, r.chunk_ids AS chunk_ids
                """,
                word=word,
            )
            return [dict(record) for record in result]
