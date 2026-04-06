"""Step definitions for raptor_pipeline module.

Registered steps:
    raptor_pipeline.run  — Run RAPTOR indexing (chunking → RAPTOR tree → KG)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from dagster_dsl.steps import register_step
from raptor_pipeline.schemas import RaptorPipelineConfig

log = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "raptor_pipeline" / "conf"


@register_step(
    "raptor_pipeline.run",
    description="RAPTOR Pipeline — индексация документов в графовое + векторное хранилище",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=RaptorPipelineConfig,
    tags={"module": "raptor_pipeline", "type": "indexing"},
)
def raptor_run_step(cfg):
    """Execute raptor_pipeline run logic.

    Replicates the CLI ``run`` command:
      1. Init DI container
      2. Call pipeline.init_stores()
      3. Process directory or single file
      4. Close pipeline
    """
    from raptor_pipeline.containers import RaptorPipelineContainer

    container = RaptorPipelineContainer(config=cfg)
    container.wire(modules=["dagster_dsl.module_steps.raptor_pipeline_steps"])

    pipeline = container.pipeline()
    pipeline.init_stores()

    input_dir = Path(cfg.input_dir)

    try:
        if cfg.input_file:
            path = input_dir / cfg.input_file
            result = pipeline.process_file(path)
            return {"mode": "single_file", "file": str(path), "result": result}
        else:
            results = pipeline.process_directory(input_dir)
            return {"mode": "directory", "input_dir": str(input_dir), "files_processed": len(results)}
    finally:
        pipeline.close()
