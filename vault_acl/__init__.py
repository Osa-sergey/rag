"""Vault Access Control List (ACL) system. 

Provides RBAC & Path-based fine-grained permission control.
"""
from __future__ import annotations

from .models import Permission, AccessRule, AclPolicy, UserIdentity
from .engine import RuleResolver
from .loader import load_policy, load_policy_from_yaml
from .gatekeeper import VaultGatekeeper
from .frontmatter import parse_frontmatter_acl, extract_acl_from_markdown
from .grants import (
    AccessRequest, AccessGrant, GrantStore,
    RequestStatus, GrantType,
)

__all__ = [
    "Permission",
    "AccessRule",
    "AclPolicy",
    "UserIdentity",
    "RuleResolver",
    "VaultGatekeeper",
    "load_policy",
    "load_policy_from_yaml",
    "parse_frontmatter_acl",
    "extract_acl_from_markdown",
    "AccessRequest",
    "AccessGrant",
    "GrantStore",
    "RequestStatus",
    "GrantType",
]
