import pytest
from vault_acl.loader import load_policy_from_yaml, _parse_permissions
from vault_acl.models import Permission

def test_parse_permissions():
    perms = _parse_permissions(["read", "write"])
    assert Permission.READ in perms
    assert Permission.WRITE in perms
    assert Permission.DELETE not in perms
    
    perms = _parse_permissions(["all"])
    assert perms == Permission.ALL

def test_load_policy_from_yaml():
    yaml_content = """
    default_deny: true
    roles:
      admin: [alice]
      editor: [bob, charlie]
    
    rules:
      - pattern: "**/*"
        roles: [admin]
        permissions: [read, write, delete, create]
        priority: 100
        
      - pattern: "projects/secret/**"
        users: [bob]
        permissions: [read]
        priority: 50
    """
    
    policy = load_policy_from_yaml(yaml_content)
    assert policy.default_deny is True
    assert policy.roles == {"admin": ["alice"], "editor": ["bob", "charlie"]}
    assert len(policy.rules) == 2
    
    r1 = policy.rules[0]
    assert r1.pattern == "**/*"
    assert "admin" in r1.roles
    assert r1.permissions == Permission.ALL
    assert r1.priority == 100
    
    r2 = policy.rules[1]
    assert r2.pattern == "projects/secret/**"
    assert "bob" in r2.users
    assert r2.permissions == Permission.READ
    assert r2.priority == 50
