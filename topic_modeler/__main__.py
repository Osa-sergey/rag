"""CLI entry point for Topic Modeler.

Usage:
    python -m topic_modeler mode=train
    python -m topic_modeler mode=add_article article_path=parsed_yaml/957000_20260204_130209.yaml
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import hydra
from omegaconf import DictConfig

logger = logging.getLogger(__name__)


@hydra.main(
    config_path="conf",
    config_name="config",
    version_base=None,
)
def main(cfg: DictConfig) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][%(name)s][%(levelname)s] - %(message)s",
    )

    from topic_modeler.modeler import TopicModeler

    mode = cfg.get("mode", "train")
    modeler = TopicModeler(cfg)

    try:
        if mode == "train":
            input_dir = Path(cfg.get("input_dir", "parsed_yaml"))
            csv_paths = [Path(p) for p in cfg.get("csv_paths", [])]
            result = modeler.train(input_dir, csv_paths)
            logger.info("Train result: %s", result)

        elif mode == "add_article":
            article_path = cfg.get("article_path")
            if not article_path:
                logger.error("article_path is required for mode=add_article")
                sys.exit(1)
            csv_paths = [Path(p) for p in cfg.get("csv_paths", [])]
            result = modeler.add_article(Path(article_path), csv_paths)
            logger.info("Add article result: %s", result)

        else:
            logger.error("Unknown mode: %s. Use 'train' or 'add_article'.", mode)
            sys.exit(1)
    finally:
        modeler.close()


if __name__ == "__main__":
    main()
