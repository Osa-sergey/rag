"""Tests for the access request and grant system."""
import pytest
from datetime import datetime, timedelta, timezone

from vault_acl.grants import (
    AccessRequest, AccessGrant, GrantStore,
    RequestStatus, GrantType,
)
from vault_acl.engine import RuleResolver
from vault_acl.models import Permission, AccessRule, AclPolicy


# ── GrantStore lifecycle ─────────────────────────────────────────────

class TestGrantStoreLifecycle:

    def _make_store(self) -> GrantStore:
        return GrantStore()

    def test_create_and_approve(self):
        store = self._make_store()
        req = store.create_request(
            requester="dave",
            file_path="secrets/plan.md",
            owner="alice",
            permissions=Permission.READ,
            grant_type=GrantType.TEMPORARY,
            ttl_minutes=30,
            reason="Need to review for meeting",
        )
        assert req.status == RequestStatus.PENDING
        assert req.requester == "dave"

        # Owner approves
        grant = store.approve(req.id, approved_by="alice")
        assert grant.user == "dave"
        assert grant.permissions == Permission.READ
        assert grant.is_active is True
        assert grant.expires_at is not None

        # Request status updated
        assert store.get_request(req.id).status == RequestStatus.APPROVED

    def test_deny_request(self):
        store = self._make_store()
        req = store.create_request(
            requester="dave", file_path="x.md", owner="alice",
        )
        denied = store.deny(req.id, denied_by="alice")
        assert denied.status == RequestStatus.DENIED

    def test_only_owner_can_approve(self):
        store = self._make_store()
        req = store.create_request(
            requester="dave", file_path="x.md", owner="alice",
        )
        with pytest.raises(PermissionError):
            store.approve(req.id, approved_by="bob")

    def test_only_owner_can_deny(self):
        store = self._make_store()
        req = store.create_request(
            requester="dave", file_path="x.md", owner="alice",
        )
        with pytest.raises(PermissionError):
            store.deny(req.id, denied_by="bob")

    def test_cannot_approve_twice(self):
        store = self._make_store()
        req = store.create_request(
            requester="dave", file_path="x.md", owner="alice",
        )
        store.approve(req.id, approved_by="alice")
        with pytest.raises(ValueError):
            store.approve(req.id, approved_by="alice")

    def test_revoke_grant(self):
        store = self._make_store()
        req = store.create_request(
            requester="dave", file_path="x.md", owner="alice",
        )
        grant = store.approve(req.id, approved_by="alice")
        assert len(store.active_grants_for_user("dave")) == 1

        store.revoke(grant.id, revoked_by="alice")
        assert len(store.active_grants_for_user("dave")) == 0
        assert store.get_request(req.id).status == RequestStatus.REVOKED

    def test_permanent_grant(self):
        store = self._make_store()
        req = store.create_request(
            requester="bob", file_path="doc.md", owner="alice",
            grant_type=GrantType.PERMANENT, ttl_minutes=None,
        )
        grant = store.approve(req.id, approved_by="alice")
        assert grant.expires_at is None
        assert grant.is_expired is False
        assert grant.is_active is True


# ── Grant expiration ─────────────────────────────────────────────────

class TestGrantExpiration:

    def test_expired_grant_is_not_active(self):
        grant = AccessGrant(
            id="test",
            user="dave",
            file_path="x.md",
            permissions=Permission.READ,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        assert grant.is_expired is True
        assert grant.is_active is False

    def test_future_grant_is_active(self):
        grant = AccessGrant(
            id="test",
            user="dave",
            file_path="x.md",
            permissions=Permission.READ,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert grant.is_active is True


# ── Queries ──────────────────────────────────────────────────────────

class TestGrantStoreQueries:

    def test_pending_for_owner(self):
        store = GrantStore()
        store.create_request(requester="dave", file_path="a.md", owner="alice")
        store.create_request(requester="bob", file_path="b.md", owner="alice")
        store.create_request(requester="dave", file_path="c.md", owner="charlie")

        pending = store.pending_for_owner("alice")
        assert len(pending) == 2

    def test_active_grants_for_file(self):
        store = GrantStore()
        r1 = store.create_request(requester="dave", file_path="doc.md", owner="alice")
        r2 = store.create_request(requester="bob", file_path="doc.md", owner="alice")
        r3 = store.create_request(requester="dave", file_path="other.md", owner="alice")

        store.approve(r1.id, approved_by="alice")
        store.approve(r2.id, approved_by="alice")
        store.approve(r3.id, approved_by="alice")

        grants = store.active_grants_for_file("doc.md")
        assert len(grants) == 2


# ── Integration with RuleResolver ────────────────────────────────────

class TestGrantsInResolver:

    def test_approved_grant_gives_access(self):
        """dave (viewer) can't write globally, but approved grant gives write."""
        store = GrantStore()
        policy = AclPolicy(
            roles={"viewer": ["dave"]},
            rules=[
                AccessRule.allow("**/*", Permission.READ, roles=["viewer"], priority=10),
            ],
            default_deny=True,
        )
        resolver = RuleResolver(policy, grant_store=store)

        # Before grant
        assert resolver.can("dave", "secrets/plan.md", Permission.WRITE) is False

        # Create and approve grant
        req = store.create_request(
            requester="dave", file_path="secrets/plan.md", owner="alice",
            permissions=Permission.READ | Permission.WRITE,
            grant_type=GrantType.TEMPORARY, ttl_minutes=60,
        )
        store.approve(req.id, approved_by="alice")

        # After grant
        assert resolver.can("dave", "secrets/plan.md", Permission.WRITE) is True
        assert resolver.can("dave", "secrets/plan.md", Permission.READ) is True
        # Other files still denied for write
        assert resolver.can("dave", "other/file.md", Permission.WRITE) is False

    def test_revoked_grant_removes_access(self):
        store = GrantStore()
        policy = AclPolicy(
            roles={"viewer": ["dave"]},
            rules=[AccessRule.allow("**/*", Permission.READ, roles=["viewer"])],
            default_deny=True,
        )
        resolver = RuleResolver(policy, grant_store=store)

        req = store.create_request(
            requester="dave", file_path="x.md", owner="alice",
            permissions=Permission.WRITE,
        )
        grant = store.approve(req.id, approved_by="alice")
        assert resolver.can("dave", "x.md", Permission.WRITE) is True

        store.revoke(grant.id, revoked_by="alice")
        assert resolver.can("dave", "x.md", Permission.WRITE) is False
