"""Parser for inline ACL rules embedded in Obsidian file YAML frontmatter.

A markdown file can declare per-file access rules in frontmatter:

    ---
    title: Secret Project Plan
    acl:
      - users: [bob]
        permissions: [read, write]
      - roles: [viewer]
        permissions: [read]
      - roles: [editor]
        permissions: [write, delete]
        deny: true
    ---
    # Content here ...

These rules are scoped to exactly this file (pattern = file's own path).
By default, inline rules receive a high base priority (200) so they
override global policy.yaml rules.  The base can be tuned via
``inline_priority_base`` param.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .loader import _parse_permissions
from .models import AccessRule, Permission


# ── Default priority for inline rules ────────────────────────────────
INLINE_PRIORITY_BASE = 200


def parse_frontmatter_acl(
    frontmatter: dict[str, Any],
    file_path: str,
    *,
    priority_base: int = INLINE_PRIORITY_BASE,
) -> list[AccessRule]:
    """Extract ACL rules from a parsed frontmatter dict.

    Args:
        frontmatter: Already-parsed YAML frontmatter dict
                     (e.g. from vault_parser.parser.parse_frontmatter).
        file_path: Relative path of the file within the vault.
                   Used as the exact pattern for generated rules.
        priority_base: Base priority for inline rules (default 200).
                       Individual entries can add a relative ``priority``
                       offset on top of this base.

    Returns:
        List of AccessRule objects scoped to ``file_path``.
    """
    acl_block = frontmatter.get("acl")
    if not acl_block:
        return []

    if not isinstance(acl_block, list):
        return []

    rules: list[AccessRule] = []
    for idx, entry in enumerate(acl_block):
        if not isinstance(entry, dict):
            continue

        perms_raw = entry.get("permissions", [])
        if isinstance(perms_raw, str):
            perms_raw = [perms_raw]

        try:
            permissions = _parse_permissions(perms_raw)
        except ValueError:
            continue  # skip malformed entries

        # Priority: base + optional per-entry offset
        offset = int(entry.get("priority", 0))
        priority = priority_base + offset

        rule = AccessRule(
            pattern=file_path,
            permissions=permissions,
            deny=bool(entry.get("deny", False)),
            priority=priority,
            roles=entry.get("roles", []),
            users=entry.get("users", []),
        )
        rules.append(rule)

    return rules


def extract_acl_from_markdown(
    text: str,
    file_path: str,
    *,
    priority_base: int = INLINE_PRIORITY_BASE,
) -> list[AccessRule]:
    """Read raw markdown, parse frontmatter, and extract inline ACL rules.

    Convenience wrapper combining YAML frontmatter parsing with ACL extraction.

    Args:
        text: Full markdown file content (with ``---`` frontmatter).
        file_path: Relative path within the vault.
        priority_base: Base priority for inline rules.

    Returns:
        List of AccessRule objects (empty if no ``acl:`` block found).
    """
    if not text.startswith("---"):
        return []

    end_idx = text.find("\n---", 3)
    if end_idx == -1:
        return []

    fm_raw = text[3:end_idx].strip()
    try:
        fm = yaml.safe_load(fm_raw)
        if not isinstance(fm, dict):
            return []
    except yaml.YAMLError:
        return []

    return parse_frontmatter_acl(fm, file_path, priority_base=priority_base)
