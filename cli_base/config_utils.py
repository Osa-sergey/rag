"""Shared configuration utilities.

Used by all DI containers to convert Pydantic models to OmegaConf DictConfig.
"""
from __future__ import annotations

from omegaconf import OmegaConf, DictConfig
from pydantic import BaseModel


def to_dictconfig(obj) -> DictConfig:
    """Convert a Pydantic model, dict, or DictConfig to OmegaConf DictConfig.

    Components use ``cfg.get(key, default)`` — an OmegaConf API.
    When configs arrive from the Click+Hydra+Pydantic pipeline they are
    Pydantic models, so we must convert at the DI boundary.
    """
    if isinstance(obj, DictConfig):
        return obj
    if isinstance(obj, BaseModel):
        return OmegaConf.create(obj.model_dump(by_alias=True))
    if isinstance(obj, dict):
        return OmegaConf.create(obj)
    return obj
