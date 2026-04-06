"""Step definitions for topic_modeler module.

Registered steps:
    topic_modeler.train        — Train BERTopic model
    topic_modeler.add_article  — Predict topic for a new article
"""
from __future__ import annotations

import logging
from pathlib import Path

from dagster_dsl.steps import register_step
from topic_modeler.schemas import TopicModelerConfig

log = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "topic_modeler" / "conf"


@register_step(
    "topic_modeler.train",
    description="Обучить BERTopic на всех статьях",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=TopicModelerConfig,
    tags={"module": "topic_modeler", "type": "training"},
)
def topic_train_step(cfg):
    """Execute topic_modeler train logic.

    Replicates the CLI ``train`` command:
      1. Init DI container
      2. Call modeler.train()
      3. Close modeler
    """
    from topic_modeler.containers import TopicModelerContainer

    container = TopicModelerContainer(config=cfg)

    modeler = container.topic_modeler()
    try:
        result = modeler.train(
            input_dir=Path(cfg.input_dir),
            csv_paths=[Path(p) for p in cfg.csv_paths] if cfg.csv_paths else [],
        )
        return result
    finally:
        modeler.close()


@register_step(
    "topic_modeler.add_article",
    description="Предсказать топик для новой статьи",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=TopicModelerConfig,
    tags={"module": "topic_modeler", "type": "prediction"},
)
def topic_add_article_step(cfg):
    """Execute topic_modeler add-article logic."""
    from topic_modeler.containers import TopicModelerContainer

    container = TopicModelerContainer(config=cfg)

    modeler = container.topic_modeler()
    try:
        article_path = Path(cfg.article_path) if hasattr(cfg, "article_path") and cfg.article_path else None
        if article_path is None:
            raise ValueError("article_path is required for topic_modeler.add_article")

        csv_paths = [Path(p) for p in cfg.csv_paths] if cfg.csv_paths else None
        result = modeler.add_article(article_path, csv_paths)
        return result
    finally:
        modeler.close()
