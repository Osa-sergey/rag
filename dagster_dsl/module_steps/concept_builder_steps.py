"""Step definitions for concept_builder module.

Registered steps:
    concept_builder.process  — Full cross-article concept building pipeline
"""
from __future__ import annotations

import logging
from pathlib import Path

from dagster_dsl.steps import register_step
from concept_builder.schemas import ConceptBuilderConfig

log = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "concept_builder" / "conf"


@register_step(
    "concept_builder.process",
    description="Кросс-статейное объединение ключевых слов в понятия",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=ConceptBuilderConfig,
    tags={"module": "concept_builder", "type": "concept_building"},
)
def concept_process_step(cfg):
    """Execute concept_builder process logic.

    Replicates the CLI ``process`` command:
      1. Init DI container
      2. Select articles via ArticleSelector
      3. Run processor.process()
      4. Return result
    """
    from concept_builder.containers import ConceptBuilderContainer

    container = ConceptBuilderContainer(config=cfg)
    selector = container.article_selector()
    processor = container.processor()

    # Article selection — use config values
    base_article = getattr(cfg, "base_article", None)
    strategy = getattr(cfg, "strategy", "bfs")
    max_articles = getattr(cfg, "max_articles", None)
    article_ids_str = getattr(cfg, "article_ids", None)

    if article_ids_str:
        # Explicit list of article IDs
        selected = [a.strip() for a in article_ids_str.split(",") if a.strip()]
    elif base_article:
        selected = selector.select(
            base_article=str(base_article),
            strategy=strategy,
            max_articles=max_articles,
        )
    else:
        raise ValueError(
            "concept_builder.process requires either 'base_article' or "
            "'article_ids' in config/overrides."
        )

    if not selected:
        log.warning("No articles selected for concept building")
        return {"concepts_created": 0, "relations_created": 0}

    log.info("Processing %d articles", len(selected))
    result = processor.process(selected)

    container.graph_store().close()
    return result
