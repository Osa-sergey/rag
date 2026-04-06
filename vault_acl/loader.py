"""YAML loader for Vault ACL policies."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import AccessRule, AclPolicy, Permission


def _parse_permissions(perms_list: list[str]) -> Permission:
    """Parse a list of permission strings into a Permission bitflag."""
    result = Permission.NONE
    mapping = {
        "read": Permission.READ,
        "write": Permission.WRITE,
        "delete": Permission.DELETE,
        "create": Permission.CREATE,
        "all": Permission.ALL,
    }
    for p in perms_list:
        p_lower = p.lower()
        if p_lower in mapping:
            result |= mapping[p_lower]
        else:
            raise ValueError(f"Unknown permission: {p}")
    return result


def load_policy_from_yaml(content: str) -> AclPolicy:
    """Parse YAML string content into an AclPolicy object."""
    data: dict[str, Any] = yaml.safe_load(content) or {}
    
    roles = data.get("roles", {})
    default_deny = data.get("default_deny", True)
    
    rules = []
    for rule_data in data.get("rules", []):
        perms = rule_data.get("permissions", [])
        if isinstance(perms, str):
            perms = [perms]
            
        rule = AccessRule(
            pattern=rule_data.get("pattern", "**/*"),
            permissions=_parse_permissions(perms),
            deny=rule_data.get("deny", False),
            priority=rule_data.get("priority", 0),
            roles=rule_data.get("roles", []),
            users=rule_data.get("users", []),
        )
        rules.append(rule)
        
    return AclPolicy(
        roles=roles,
        rules=rules,
        default_deny=default_deny,
    )


def load_policy(path: Path | str) -> AclPolicy:
    """Load an ACL policy from a YAML file."""
    text = Path(path).read_text(encoding="utf-8")
    return load_policy_from_yaml(text)
