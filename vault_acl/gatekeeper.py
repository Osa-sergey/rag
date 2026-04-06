"""Facade for Vault Access Control List operations."""
from __future__ import annotations

from typing import Iterable

from interfaces.vault_acl import BaseAccessResolver
from .engine import RuleResolver
from .models import Permission, UserIdentity


class VaultGatekeeper:
    """High-level facade over RuleResolver.
    
    Provides convenient `can_read`, `can_write`, etc., checks.
    """

    def __init__(self, resolver: BaseAccessResolver):
        self.resolver = resolver

    @property
    def engine(self) -> BaseAccessResolver:
        return self.resolver

    def can_read(self, user: UserIdentity | str, file_path: str) -> bool:
        return self.resolver.can(user, file_path, Permission.READ)

    def can_write(self, user: UserIdentity | str, file_path: str) -> bool:
        return self.resolver.can(user, file_path, Permission.WRITE)

    def can_delete(self, user: UserIdentity | str, file_path: str) -> bool:
        return self.resolver.can(user, file_path, Permission.DELETE)

    def can_create(self, user: UserIdentity | str, file_path: str) -> bool:
        return self.resolver.can(user, file_path, Permission.CREATE)

    def filter_readable(self, user: UserIdentity | str, paths: Iterable[str]) -> list[str]:
        return self.resolver.filter_accessible(user, paths, Permission.READ)

    def filter_writable(self, user: UserIdentity | str, paths: Iterable[str]) -> list[str]:
        return self.resolver.filter_accessible(user, paths, Permission.WRITE)

    def filter_deletable(self, user: UserIdentity | str, paths: Iterable[str]) -> list[str]:
        return self.resolver.filter_accessible(user, paths, Permission.DELETE)

    def get_user_permissions(self, user: UserIdentity | str, file_path: str) -> Permission:
        """Get the full permission bitmask for custom UI logic."""
        return self.resolver.resolve_permissions(user, file_path)
