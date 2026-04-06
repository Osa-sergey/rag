"""Core models for Vault Access Control List (ACL) system."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Flag, auto
from typing import Any


class Permission(Flag):
    """File access permissions using bitflags for efficient checking."""
    NONE = 0
    READ = auto()
    WRITE = auto()
    DELETE = auto()
    CREATE = auto()
    ALL = READ | WRITE | DELETE | CREATE


@dataclass
class UserIdentity:
    """Represents a user requesting access."""
    username: str
    roles: list[str] = field(default_factory=list)


@dataclass
class AccessRule:
    """A single access control rule."""
    pattern: str
    permissions: Permission
    deny: bool = False
    priority: int = 0
    roles: list[str] = field(default_factory=list)
    users: list[str] = field(default_factory=list)

    @classmethod
    def allow(
        cls,
        pattern: str,
        permissions: Permission,
        roles: list[str] | None = None,
        users: list[str] | None = None,
        priority: int = 0,
    ) -> AccessRule:
        """Create an ALLOW rule."""
        return cls(
            pattern=pattern,
            permissions=permissions,
            deny=False,
            priority=priority,
            roles=roles or [],
            users=users or [],
        )

    @classmethod
    def deny_rule(
        cls,
        pattern: str,
        permissions: Permission,
        roles: list[str] | None = None,
        users: list[str] | None = None,
        priority: int = 0,
    ) -> AccessRule:
        """Create a DENY rule."""
        return cls(
            pattern=pattern,
            permissions=permissions,
            deny=True,
            priority=priority,
            roles=roles or [],
            users=users or [],
        )


@dataclass
class AclPolicy:
    """Full policy definition covering all users and rules."""
    roles: dict[str, list[str]] = field(default_factory=dict)
    rules: list[AccessRule] = field(default_factory=list)
    default_deny: bool = True

    def get_user_roles(self, username: str) -> list[str]:
        """Resolve all roles assigned to the given user."""
        return [
            role for role, users in self.roles.items()
            if username in users
        ]
