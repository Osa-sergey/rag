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
        if check_connectivity and len(article_ids) > 1:
            if not self._check_connectivity(article_ids):
                raise ValueError(
                    f"Articles {article_ids} are not all connected "
                    f"via REFERENCES. Use --no-check-connectivity to skip."
                )

        logger.info(
            "ArticleSelector: explicit %d articles (connectivity_check=%s)",
            len(article_ids), check_connectivity,
        )
        return article_ids

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
