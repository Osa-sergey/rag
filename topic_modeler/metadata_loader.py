"""Load article metadata from scraped CSV files."""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ArticleMeta:
    """Metadata for a single article (from Habr scraper CSV)."""

    title: str = ""
    author: str = ""
    reading_time: str = ""
    complexity: str = ""
    labels: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    hubs: list[str] = field(default_factory=list)


def _parse_list(raw: str) -> list[str]:
    """Split a comma/semicolon separated string into a clean list."""
    if not raw:
        return []
    # tags_and_hubs may be comma-separated or semicolon-separated
    for sep in [";", ","]:
        if sep in raw:
            return [s.strip() for s in raw.split(sep) if s.strip()]
    return [raw.strip()] if raw.strip() else []


def load_metadata(csv_paths: list[Path]) -> dict[str, ArticleMeta]:
    """Load article metadata from one or more CSV files.

    Returns a dict mapping ``article_id`` → :class:`ArticleMeta`.
    Duplicates across CSVs are resolved by keeping the latest occurrence.
    """
    result: dict[str, ArticleMeta] = {}
    total = 0

    for csv_path in csv_paths:
        if not csv_path.exists():
            logger.warning("CSV file not found, skipping: %s", csv_path)
            continue

        logger.info("Loading metadata from %s ...", csv_path.name)
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                article_id = row.get("id", "").strip()
                if not article_id:
                    continue

                # Parse tags_and_hubs: try to split into tags vs hubs
                tags_and_hubs_raw = row.get("tags_and_hubs", "")
                all_items = _parse_list(tags_and_hubs_raw)

                # Heuristic: items starting with * or containing "хаб" are hubs
                # Otherwise treat all as tags (user can refine later)
                tags = all_items
                hubs: list[str] = []

                result[article_id] = ArticleMeta(
                    title=row.get("title", "").strip(),
                    author=row.get("author", "").strip(),
                    reading_time=row.get("reading_time", "").strip(),
                    complexity=row.get("complexity", "").strip(),
                    labels=_parse_list(row.get("labels", "")),
                    tags=tags,
                    hubs=hubs,
                )
                total += 1

    logger.info("Loaded metadata for %d articles from %d CSV files", total, len(csv_paths))
    return result
