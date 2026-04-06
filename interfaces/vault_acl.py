"""Interfaces for the Vault Access Control List system."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from vault_acl.models import Permission, AccessRule, UserIdentity


class BaseAccessResolver(ABC):
    """Core engine interface for resolving file access permissions."""

    @abstractmethod
    def resolve_permissions(self, user: UserIdentity | str, file_path: str) -> Permission:
        """Calculate effective permissions a user has for a target file.

        Args:
            user: UserIdentity instance, or str (username), which will resolve roles via policy.
            file_path: Relative path within the vault.
            
        Returns:
            Permission flag (e.g. Permission.READ | Permission.WRITE)
        """
        ...

    @abstractmethod
    def can(self, user: UserIdentity | str, file_path: str, action: Permission) -> bool:
        """Check if a User has a specific permission on a file.

        Args:
            user: UserIdentity or username string.
            file_path: Relative path within the vault.
            action: The permission being requested (can be composite).
            
        Returns:
            True if user has ALL specified permissions, False otherwise.
        """
        ...

    @abstractmethod
    def filter_accessible(self, user: UserIdentity | str, paths: Iterable[str], action: Permission) -> list[str]:
        """Filter a list of file paths down to those the user has `action` access to.

        Args:
            user: UserIdentity or username string.
            paths: List/iterable of file paths to check.
            action: The permission required for the path to be included.
            
        Returns:
            List of accessible paths.
        """
        ...

    @abstractmethod
    def effective_rules(self, user: UserIdentity | str, file_path: str) -> list[AccessRule]:
        """Return exactly which rules match and affect the user for a file.
        Useful for debugging and auditing access logic.
        """
        ...
