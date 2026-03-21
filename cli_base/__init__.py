"""Shared CLI base — common utilities for Click + Hydra + Pydantic CLI modules."""
from cli_base.config_loader import load_config
from cli_base.common_commands import add_common_commands
from cli_base.logging import setup_logging, get_console

__all__ = ["load_config", "add_common_commands", "setup_logging", "get_console"]
