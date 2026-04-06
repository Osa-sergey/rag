"""Access request and grant system for Vault ACL.

Allows users to request access to files from the file owner.
Grants can be permanent or time-limited (temporary).

Lifecycle:
    1. User creates an AccessRequest (status=PENDING)
    2. File owner reviews and approves/denies
    3. Approved request becomes an AccessGrant
    4. GrantStore feeds active grants into RuleResolver
    5. Expired grants are automatically ignored
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from .models import Permission


class RequestStatus(Enum):
    """Lifecycle status of an access request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    REVOKED = "revoked"     # owner revoked a previously approved grant
    EXPIRED = "expired"     # auto-set when TTL runs out


class GrantType(Enum):
    """Duration type of an access grant."""
    PERMANENT = "permanent"
    TEMPORARY = "temporary"


@dataclass
class AccessRequest:
    """A request from one user to access a file owned by another."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    requester: str = ""           # username requesting access
    file_path: str = ""           # vault-relative path
    owner: str = ""               # file creator / owner
    permissions: Permission = Permission.READ
    grant_type: GrantType = GrantType.TEMPORARY
    ttl_minutes: int | None = 60  # None for permanent
    reason: str = ""              # optional justification
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    resolved_by: str | None = None


@dataclass
class AccessGrant:
    """An active permission grant derived from an approved AccessRequest."""
    id: str = ""                  # same id as the originating request
    user: str = ""                # who received the grant
    file_path: str = ""
    permissions: Permission = Permission.READ
    grant_type: GrantType = GrantType.TEMPORARY
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None   # None = permanent
    granted_by: str = ""                 # owner who approved

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_active(self) -> bool:
        return not self.is_expired

    @classmethod
    def from_request(cls, request: AccessRequest) -> AccessGrant:
        """Create a grant from an approved request."""
        now = datetime.now(timezone.utc)
        expires = None
        if request.grant_type == GrantType.TEMPORARY and request.ttl_minutes:
            expires = now + timedelta(minutes=request.ttl_minutes)

        return cls(
            id=request.id,
            user=request.requester,
            file_path=request.file_path,
            permissions=request.permissions,
            grant_type=request.grant_type,
            granted_at=now,
            expires_at=expires,
            granted_by=request.owner,
        )


class GrantStore:
    """In-memory store for access requests and active grants.

    In production this would be backed by a database or a YAML/JSON
    file inside the vault.  The in-memory version is sufficient for
    the core logic and tests.
    """

    def __init__(self) -> None:
        self._requests: dict[str, AccessRequest] = {}
        self._grants: dict[str, AccessGrant] = {}

    # ── Request lifecycle ────────────────────────────────────────────

    def create_request(
        self,
        requester: str,
        file_path: str,
        owner: str,
        permissions: Permission = Permission.READ,
        grant_type: GrantType = GrantType.TEMPORARY,
        ttl_minutes: int | None = 60,
        reason: str = "",
    ) -> AccessRequest:
        """Create a new pending access request."""
        req = AccessRequest(
            requester=requester,
            file_path=file_path,
            owner=owner,
            permissions=permissions,
            grant_type=grant_type,
            ttl_minutes=ttl_minutes,
            reason=reason,
        )
        self._requests[req.id] = req
        return req

    def approve(self, request_id: str, approved_by: str) -> AccessGrant:
        """Approve a pending request and create an active grant.

        Args:
            request_id: ID of the pending request.
            approved_by: Username of the approver (must be the owner).

        Returns:
            The newly created AccessGrant.

        Raises:
            KeyError: If request_id not found.
            PermissionError: If approved_by is not the file owner.
            ValueError: If request is not in PENDING status.
        """
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"Request {request_id!r} not found")
        if req.owner != approved_by:
            raise PermissionError(
                f"Only the owner ({req.owner!r}) can approve; "
                f"got {approved_by!r}"
            )
        if req.status != RequestStatus.PENDING:
            raise ValueError(
                f"Request {request_id!r} is {req.status.value}, not pending"
            )

        req.status = RequestStatus.APPROVED
        req.resolved_at = datetime.now(timezone.utc)
        req.resolved_by = approved_by

        grant = AccessGrant.from_request(req)
        self._grants[grant.id] = grant
        return grant

    def deny(self, request_id: str, denied_by: str) -> AccessRequest:
        """Deny a pending request.

        Raises:
            KeyError: If request_id not found.
            PermissionError: If denied_by is not the file owner.
        """
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"Request {request_id!r} not found")
        if req.owner != denied_by:
            raise PermissionError(
                f"Only the owner ({req.owner!r}) can deny; got {denied_by!r}"
            )
        if req.status != RequestStatus.PENDING:
            raise ValueError(
                f"Request {request_id!r} is {req.status.value}, not pending"
            )

        req.status = RequestStatus.DENIED
        req.resolved_at = datetime.utcnow()
        req.resolved_by = denied_by
        return req

    def revoke(self, grant_id: str, revoked_by: str) -> None:
        """Revoke an active grant.

        Raises:
            KeyError: If grant not found.
            PermissionError: If revoked_by is not the original granter.
        """
        grant = self._grants.get(grant_id)
        if grant is None:
            raise KeyError(f"Grant {grant_id!r} not found")
        if grant.granted_by != revoked_by:
            raise PermissionError(
                f"Only the granter ({grant.granted_by!r}) can revoke"
            )

        del self._grants[grant_id]

        # Also update the original request status
        if grant_id in self._requests:
            self._requests[grant_id].status = RequestStatus.REVOKED

    # ── Queries ──────────────────────────────────────────────────────

    def pending_for_owner(self, owner: str) -> list[AccessRequest]:
        """Get all pending requests that this owner needs to review."""
        return [
            r for r in self._requests.values()
            if r.owner == owner and r.status == RequestStatus.PENDING
        ]

    def pending_by_user(self, requester: str) -> list[AccessRequest]:
        """Get all pending requests made by this user."""
        return [
            r for r in self._requests.values()
            if r.requester == requester and r.status == RequestStatus.PENDING
        ]

    def active_grants_for_user(self, username: str) -> list[AccessGrant]:
        """Get all non-expired grants for a user."""
        return [
            g for g in self._grants.values()
            if g.user == username and g.is_active
        ]

    def active_grants_for_file(self, file_path: str) -> list[AccessGrant]:
        """Get all non-expired grants for a specific file."""
        norm = file_path.replace("\\", "/").lower()
        return [
            g for g in self._grants.values()
            if g.file_path.replace("\\", "/").lower() == norm and g.is_active
        ]

    def get_request(self, request_id: str) -> AccessRequest | None:
        return self._requests.get(request_id)

    def get_grant(self, grant_id: str) -> AccessGrant | None:
        return self._grants.get(grant_id)
