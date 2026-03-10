"""Neo4j graph store for keywords, relations, and article metadata."""
from __future__ import annotations

import logging

from neo4j import GraphDatabase
from omegaconf import DictConfig

from raptor_pipeline.knowledge_graph.base import Keyword, Relation

logger = logging.getLogger(__name__)


class Neo4jGraphStore:
    """Neo4j integration — stores knowledge graph.

    Graph schema:
      (:Article {id, title})
      (:Keyword {word, category})
      (:Article)-[:HAS_KEYWORD {confidence, chunk_id}]->(:Keyword)
      (:Keyword)-[:RELATED_TO {predicate, confidence, chunk_id}]->(:Keyword)
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
        ]
        with self._driver.session(database=self._database) as session:
            for q in queries:
                session.run(q)
        logger.info("Neo4j indexes ensured")

    # ------------------------------------------------------------------
    def store_article(self, article_id: str, title: str = "", summary: str = "") -> None:
        """Create or merge an Article node."""
        with self._driver.session(database=self._database) as session:
            session.run(
                "MERGE (a:Article {id: $id}) SET a.title = $title, a.summary = $summary",
                id=article_id,
                title=title,
                summary=summary,
            )

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
