"""DSL steps for Vault ACL."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from dagster_dsl.steps import register_step
from vault_acl.schemas import VaultAclConfig

log = logging.getLogger(__name__)

_CONFIG_DIR = str(Path(__file__).parent.parent.parent / "vault_acl" / "conf")

@register_step(
    "vault_acl.check_access",
    description="Check if a user has access to a specific file",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultAclConfig,
    tags={"module": "vault_acl", "type": "check"},
)
def check_access(cfg: Any) -> dict[str, Any]:
    from vault_acl.rule_resolver import RuleResolver
    
    user = getattr(cfg, "user", "")
    file_path = getattr(cfg, "file_path", "")
    action = getattr(cfg, "action", "read")
    policy_path = getattr(cfg, "policy_path", "acl_rules.yaml")
    
    resolver = RuleResolver(str(Path(policy_path)))
    allowed = resolver.can(user, file_path, action)
    perms, rules = resolver.resolve_permissions(user, file_path)
    
    return {
        "allowed": allowed,
        "permissions": perms.value if hasattr(perms, "value") else str(perms),
        "rules_matched": len(rules)
    }

@register_step(
    "vault_acl.filter_files",
    description="Filter a list of files based on user access",
    config_dir=_CONFIG_DIR,
    config_name="config",
    schema_class=VaultAclConfig,
    tags={"module": "vault_acl", "type": "filter"},
)
def filter_files(cfg: Any) -> dict[str, Any]:
    from vault_acl.rule_resolver import RuleResolver
    
    user = getattr(cfg, "user", "")
    paths = getattr(cfg, "paths", [])
    action = getattr(cfg, "action", "read")
    policy_path = getattr(cfg, "policy_path", "acl_rules.yaml")
    
    resolver = RuleResolver(str(Path(policy_path)))
    accessible = resolver.filter_accessible(user, paths, action)
    
    # We serialize Paths back to strings to avoid type issues in pipeline outputs
    str_accessible = [str(p) for p in accessible]
    
    return {
        "accessible_paths": str_accessible,
        "filtered_count": len(paths) - len(str_accessible),
        "total_count": len(paths)
    }
