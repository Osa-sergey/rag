import pytest

from vault_acl.models import Permission, AccessRule, AclPolicy
from vault_acl.engine import RuleResolver
from vault_acl.gatekeeper import VaultGatekeeper

def test_gatekeeper_facade():
    policy = AclPolicy(
        roles={"viewer": ["dave"]},
        rules=[
            AccessRule.allow("**/*", Permission.READ, roles=["viewer"]),
            AccessRule.allow("uploads/**", Permission.CREATE, roles=["viewer"])
        ],
        default_deny=True
    )
    gatekeeper = VaultGatekeeper(RuleResolver(policy))
    
    # Check permissions
    assert gatekeeper.can_read("dave", "docs/file.md") is True
    assert gatekeeper.can_write("dave", "docs/file.md") is False
    assert gatekeeper.can_create("dave", "uploads/img.png") is True
    
    # Filter methods
    paths = [
        "docs/file1.md",
        "docs/file2.md",
        "uploads/img1.png",
        "secrets/pass.txt"
    ]
    
    # Assuming dave can't read secrets/pass.txt (Wait, **/* allows everything! Let's deny secrets to be sure)
    policy.rules.append(AccessRule.deny_rule("secrets/**", Permission.READ, roles=["viewer"], priority=10))
    
    readable = gatekeeper.filter_readable("dave", paths)
    assert readable == ["docs/file1.md", "docs/file2.md", "uploads/img1.png"]
    
    creatable = gatekeeper.filter_writable("dave", paths)
    assert creatable == [] # Can't write anywhere
    
    assert gatekeeper.get_user_permissions("dave", "uploads/img.png") == (Permission.READ | Permission.CREATE)
