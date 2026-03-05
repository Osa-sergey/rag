"""Hydra entry-point for the RAPTOR pipeline."""
from __future__ import annotations

import sys

# Load environment variables from .env file before anything else
from dotenv import load_dotenv
load_dotenv()

# Force UTF-8 for Windows console to prevent charmap errors with Cyrillic
# MUST be done before importing logging or hydra
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

import logging
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf

from raptor_pipeline.pipeline import RaptorPipeline

logger = logging.getLogger(__name__)

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    """Run the RAPTOR pipeline with Hydra configuration."""
    logger.info("Config:\n%s", OmegaConf.to_yaml(cfg))

    pipeline = RaptorPipeline(cfg)
    pipeline.init_stores()

    input_dir = Path(cfg.get("input_dir", "parsed_yaml"))

    # Single file mode
    input_file = cfg.get("input_file", None)
    if input_file:
        path = input_dir / input_file
        result = pipeline.process_file(path)
        logger.info("Result: %s", result)
    else:
        # Batch mode
        results = pipeline.process_directory(input_dir)
        logger.info("Processed %d files", len(results))
        for r in results:
            logger.info("  %s", r)

    pipeline.close()


if __name__ == "__main__":
    main()
