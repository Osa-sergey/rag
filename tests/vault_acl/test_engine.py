import pytest

from vault_acl.models import Permission, AccessRule, AclPolicy, UserIdentity
from vault_acl.engine import RuleResolver


def test_basic_allow_deny():
    policy = AclPolicy(
        roles={"admin": ["alice"]},
        rules=[
            AccessRule.allow("**/*", Permission.READ, roles=["admin"], priority=10),
            AccessRule.deny_rule("secrets/*.md", Permission.READ, roles=["admin"], priority=20)
        ],
        default_deny=True
    )
    resolver = RuleResolver(policy)
    
    # Alice can read normal files
    assert resolver.can("alice", "docs/hello.md", Permission.READ) is True
    # Alice CANNOT read secrets due to higher priority deny rule
    assert resolver.can("alice", "secrets/password.md", Permission.READ) is False
    # Unknown user cannot read anything
    assert resolver.can("bob", "docs/hello.md", Permission.READ) is False


def test_priority_and_deny_overrides():
    policy = AclPolicy(
        roles={"editor": ["bob"]},
        rules=[
            # Bob can read and write everything
            AccessRule.allow("**/*", Permission.READ | Permission.WRITE, roles=["editor"], priority=10),
            # Bob cannot delete daily notes
            AccessRule.deny_rule("daily/*.md", Permission.DELETE, roles=["editor"], priority=20),
            # Bob is explicitly allowed to delete one specific daily note
            AccessRule.allow("daily/2025-01-01.md", Permission.DELETE, users=["bob"], priority=30)
        ],
        default_deny=True
    )
    resolver = RuleResolver(policy)
    
    # Check general editor permissions
    assert resolver.can("bob", "projects/p1.md", Permission.READ | Permission.WRITE) is True
    # Deletion of projects is not explicitly allowed, so default_deny kicks in for DELETE 
    # (wait, the rule gives READ | WRITE, so DELETE is not granted)
    assert resolver.can("bob", "projects/p1.md", Permission.DELETE) is False

    # But what if we added ALL to editor?
    policy.rules[0].permissions = Permission.ALL
    
    # Now Bob can delete projects
    assert resolver.can("bob", "projects/p1.md", Permission.DELETE) is True
    # Bob CANNOT delete daily notes
    assert resolver.can("bob", "daily/2025-02-02.md", Permission.DELETE) is False
    assert resolver.can("bob", "daily/2025-02-02.md", Permission.READ) is True
    
    # Bob CAN delete the specific exception note
    assert resolver.can("bob", "daily/2025-01-01.md", Permission.DELETE) is True


def test_specificity_tie_breaker():
    policy = AclPolicy(
        rules=[
            # Two rules, same priority. One is more specific.
            AccessRule.allow("**/*", Permission.READ, users=["charlie"], priority=10),
            AccessRule.deny_rule("daily/2025-*.md", Permission.READ, users=["charlie"], priority=10)
        ]
    )
    resolver = RuleResolver(policy)
    
    assert resolver.can("charlie", "docs/hello.md", Permission.READ) is True
    assert resolver.can("charlie", "daily/2025-05-05.md", Permission.READ) is False

    # Specificity penalty test:
    # "daily/2025-05-05.md" has higher specificity than "daily/2025-*.md"
    policy.rules.append(
         AccessRule.allow("daily/2025-05-05.md", Permission.READ, users=["charlie"], priority=10)
    )
    assert resolver.can("charlie", "daily/2025-05-05.md", Permission.READ) is True
