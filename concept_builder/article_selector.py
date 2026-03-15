"""Article selector — BFS/DFS traversal over REFERENCES graph."""
from __future__ import annotations

import logging
from collections import deque
from typing import Any

from interfaces import BaseArticleSelector

logger = logging.getLogger(__name__)


class ArticleSelector(BaseArticleSelector):
    """Select related articles by traversing the REFERENCES graph in Neo4j."""

    def __init__(self, graph_store: Any) -> None:
        self._gs = graph_store

    # ──────────────────────────────────────────────────────────
    def select_by_traversal(
        self,
        base_article_id: str,
        strategy: str = "bfs",
        max_articles: int = 20,
    ) -> list[str]:
        """Traverse REFERENCES graph from *base_article_id*.

        Both directions are followed (outgoing and incoming REFERENCES).
        """
        if strategy not in ("bfs", "dfs"):
            raise ValueError(f"strategy must be 'bfs' or 'dfs', got '{strategy}'")

        # Validate base article exists
        if not self._article_exists(base_article_id):
            similar = self._find_similar_articles(base_article_id)
            msg = f"Статья '{base_article_id}' не найдена в Neo4j."
            if similar:
                msg += f" Похожие: {similar}"
            raise ValueError(msg)

        visited: set[str] = set()
        result: list[str] = []
        frontier: deque[str] = deque([base_article_id])

        while frontier and len(result) < max_articles:
            current = frontier.popleft() if strategy == "bfs" else frontier.pop()
            if current in visited:
                continue
            visited.add(current)
            result.append(current)

            neighbours = self._get_neighbours(current)
            for n in neighbours:
                if n not in visited:
                    frontier.append(n)

        logger.info(
            "ArticleSelector: %s from '%s' → %d articles (max=%d)",
            strategy.upper(), base_article_id, len(result), max_articles,
        )
        return result

    # ──────────────────────────────────────────────────────────
    def select_explicit(
        self,
        article_ids: list[str],
        check_connectivity: bool = True,
    ) -> list[str]:
        """Validate explicit list. Optionally check connectivity."""
        # Validate each article exists
        valid_ids: list[str] = []
        for aid in article_ids:
            if self._article_exists(aid):
                valid_ids.append(aid)
            else:
                similar = self._find_similar_articles(aid)
                similar_str = f" Похожие: {similar}" if similar else ""
                logger.warning("⚠️  Статья '%s' не найдена в Neo4j.%s", aid, similar_str)

        if not valid_ids:
            raise ValueError(
                f"Ни одна из указанных статей не найдена: {article_ids}"
            )

        if len(valid_ids) < len(article_ids):
            skipped = set(article_ids) - set(valid_ids)
            logger.warning(
                "Пропущены несуществующие статьи: %s. Продолжаем с %d из %d.",
                skipped, len(valid_ids), len(article_ids),
            )

        if check_connectivity and len(valid_ids) > 1:
            if not self._check_connectivity(valid_ids):
                raise ValueError(
                    f"Articles {valid_ids} are not all connected "
                    f"via REFERENCES. Use --no-check-connectivity to skip."
                )

        logger.info(
            "ArticleSelector: explicit %d articles (connectivity_check=%s)",
            len(valid_ids), check_connectivity,
        )
        return valid_ids

    # ──────────────────────────────────────────────────────────
    def _article_exists(self, article_id: str) -> bool:
        """Check if an Article node with this id exists in Neo4j."""
        with self._gs._driver.session(database=self._gs._database) as session:
            result = session.run(
                "MATCH (a:Article {id: $id}) RETURN a.id AS id LIMIT 1",
                id=article_id,
            ).single()
            return result is not None

    def _find_similar_articles(self, article_id: str, limit: int = 5) -> list[str]:
        """Find articles with similar id or article_name (for helpful error messages)."""
        with self._gs._driver.session(database=self._gs._database) as session:
            result = session.run(
                """
                MATCH (a:Article)
                WHERE a.id CONTAINS $partial
                   OR a.article_name CONTAINS $partial
                RETURN a.id AS id, a.article_name AS name
                LIMIT $limit
                """,
                partial=article_id,
                limit=limit,
            ).data()
            return [
                f"{r['id']} ({r.get('name', '')})" if r.get("name") else r["id"]
                for r in result
            ]

    # ──────────────────────────────────────────────────────────
    def _get_neighbours(self, article_id: str) -> list[str]:
        """Get articles connected to *article_id* via REFERENCES (both directions)."""
        with self._gs._driver.session(database=self._gs._database) as session:
            result = session.run(
                """
                MATCH (a:Article {id: $id})-[:REFERENCES]-(b:Article)
                RETURN DISTINCT b.id AS neighbour_id
                """,
                id=article_id,
            )
            return [r["neighbour_id"] for r in result]

    def _check_connectivity(self, article_ids: list[str]) -> bool:
        """Check if all articles are transitively connected via REFERENCES."""
        if not article_ids:
            return True

        # BFS from first article, restricted to the given set
        start = article_ids[0]
        id_set = set(article_ids)
        visited: set[str] = set()
        queue: deque[str] = deque([start])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            neighbours = self._get_neighbours(current)
            for n in neighbours:
                if n in id_set and n not in visited:
                    queue.append(n)

        # All articles in the set should be reachable
        reachable = visited & id_set
        if reachable != id_set:
            unreachable = id_set - reachable
            logger.warning(
                "Connectivity check failed: unreachable articles: %s",
                unreachable,
            )
            return False
        return True
