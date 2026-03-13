"""Load YAML via Hydra Compose API, validate with pydantic, format errors for CLI."""
from __future__ import annotations

from pathlib import Path
from typing import TypeVar, Type

import click
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def load_config(
    config_dir: str | Path,
    config_name: str,
    schema_class: Type[T],
    overrides: tuple[str, ...] = (),
    **click_overrides: object,
) -> T:
    """Load YAML config via Hydra, apply overrides, validate with pydantic.

    Args:
        config_dir: Absolute path to the directory containing YAML configs.
        config_name: Name of the root config file (without .yaml).
        schema_class: Pydantic model class to validate against.
        overrides: Raw Hydra overrides from ``-o key=value``.
        **click_overrides: Named overrides from Click options.
            Only non-None values are applied.

    Returns:
        Validated pydantic model instance.

    Raises:
        click.ClickException: On validation error with formatted messages.
    """
    hydra_overrides = list(overrides)
    for key, value in click_overrides.items():
        if value is not None:
            str_val = str(value)
            # Quote values with spaces or non-ASCII chars for Hydra lexer
            needs_quoting = " " in str_val or any(ord(c) > 127 for c in str_val)
            if needs_quoting:
                hydra_overrides.append(f"{key}='{str_val}'")
            else:
                hydra_overrides.append(f"{key}={str_val}")

    config_dir = str(Path(config_dir).resolve())
    with initialize_config_dir(config_dir=config_dir, version_base=None):
        cfg = compose(config_name=config_name, overrides=hydra_overrides)

    raw = OmegaConf.to_container(cfg, resolve=True)
    return validate(raw, schema_class)


def validate(raw: dict, schema_class: Type[T]) -> T:
    """Validate a dict against a pydantic schema, raise ClickException on error."""
    try:
        return schema_class.model_validate(raw)
    except ValidationError as e:
        lines = ["\n  Ошибки конфигурации:\n"]
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            val = err.get("input", "?")
            lines.append(f"    {loc}: {msg} (получено: {val!r})")
        raise click.ClickException("\n".join(lines))


def load_raw_config(config_dir: str | Path, config_name: str, overrides: tuple[str, ...] = ()) -> str:
    """Load raw YAML config via Hydra without validation. Returns YAML string."""
    config_dir = str(Path(config_dir).resolve())
    with initialize_config_dir(config_dir=config_dir, version_base=None):
        cfg = compose(config_name=config_name, overrides=list(overrides))
    return OmegaConf.to_yaml(cfg)
