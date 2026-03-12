"""Tests for DI container and class resolution.

Uses mocks — no real class loading or vault access.
"""
from unittest.mock import patch, MagicMock

import pytest

from vault_parser.schemas import VaultParserConfig


def _make_config(**overrides):
    """Create a minimal valid VaultParserConfig for testing."""
    defaults = {
        "vault": {
            "path": "/tmp/fake_vault",
            "daily_dir": "daily",
            "weekly_dir": "weekly",
            "monthly_dir": "monthly",
            "people_dir": "/tmp/fake_vault/people",
            "template_path": "/tmp/fake_vault/template.md",
        },
        "parser_class": "vault_parser.parser.VaultParser",
        "editor_class": "vault_parser.writer.editor.DailyNoteEditor",
    }
    defaults.update(overrides)
    return VaultParserConfig(**defaults)


class TestContainerCreation:
    """Container creates providers via resolve_class."""

    @patch("vault_parser.containers.resolve_class")
    def test_creates_parser(self, mock_resolve):
        from vault_parser.containers import _create_parser

        mock_cls = MagicMock()
        mock_resolve.return_value = mock_cls
        cfg = _make_config()

        _create_parser(cfg)
        mock_resolve.assert_called_once()
        # First arg is the class path
        assert mock_resolve.call_args[0][0] == "vault_parser.parser.VaultParser"
        # Instance was created
        mock_cls.assert_called_once()

    @patch("vault_parser.containers.resolve_class")
    def test_creates_editor(self, mock_resolve):
        from vault_parser.containers import _create_editor

        mock_cls = MagicMock()
        mock_resolve.return_value = mock_cls
        cfg = _make_config()

        _create_editor(cfg)
        mock_resolve.assert_called_once()
        assert mock_resolve.call_args[0][0] == "vault_parser.writer.editor.DailyNoteEditor"


class TestInvalidClass:
    """resolve_class raises when class doesn't match ABC."""

    def test_invalid_class_raises(self):
        from cli_base.class_resolver import resolve_class
        from interfaces import BaseVaultParser

        with pytest.raises((TypeError, ImportError, AttributeError)):
            resolve_class("builtins.int", BaseVaultParser)
