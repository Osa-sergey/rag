"""Tests for frontmatter-based inline ACL rules."""
import pytest

from vault_acl.frontmatter import parse_frontmatter_acl, extract_acl_from_markdown
from vault_acl.engine import RuleResolver
from vault_acl.models import Permission, AccessRule, AclPolicy


# ── parse_frontmatter_acl ────────────────────────────────────────────

class TestParseFrontmatterAcl:

    def test_empty_frontmatter(self):
        assert parse_frontmatter_acl({}, "docs/file.md") == []

    def test_no_acl_key(self):
        assert parse_frontmatter_acl({"title": "Hello"}, "docs/file.md") == []

    def test_single_allow_rule(self):
        fm = {
            "acl": [
                {"users": ["bob"], "permissions": ["read", "write"]},
            ]
        }
        rules = parse_frontmatter_acl(fm, "docs/file.md")
        assert len(rules) == 1
        r = rules[0]
        assert r.pattern == "docs/file.md"
        assert r.permissions == (Permission.READ | Permission.WRITE)
        assert r.deny is False
        assert "bob" in r.users
        assert r.priority == 200  # default inline base

    def test_deny_rule(self):
        fm = {
            "acl": [
                {"roles": ["viewer"], "permissions": ["write"], "deny": True},
            ]
        }
        rules = parse_frontmatter_acl(fm, "notes/secret.md")
        assert len(rules) == 1
        assert rules[0].deny is True
        assert rules[0].permissions == Permission.WRITE

    def test_multiple_rules_with_priority_offset(self):
        fm = {
            "acl": [
                {"users": ["alice"], "permissions": ["all"]},
                {"roles": ["editor"], "permissions": ["read"], "priority": 10},
            ]
        }
        rules = parse_frontmatter_acl(fm, "x.md", priority_base=100)
        assert len(rules) == 2
        assert rules[0].priority == 100
        assert rules[1].priority == 110

    def test_malformed_entries_skipped(self):
        fm = {
            "acl": [
                "not a dict",
                {"permissions": ["bogus_perm"]},  # invalid perm
                {"users": ["bob"], "permissions": ["read"]},  # valid
            ]
        }
        rules = parse_frontmatter_acl(fm, "x.md")
        assert len(rules) == 1


# ── extract_acl_from_markdown ────────────────────────────────────────

class TestExtractAclFromMarkdown:

    def test_valid_markdown(self):
        md = """---
title: Secret
acl:
  - users: [bob]
    permissions: [read]
  - roles: [admin]
    permissions: [all]
---
# Content
Some text here.
"""
        rules = extract_acl_from_markdown(md, "projects/secret.md")
        assert len(rules) == 2
        assert rules[0].pattern == "projects/secret.md"
        assert rules[0].permissions == Permission.READ
        assert rules[1].permissions == Permission.ALL

    def test_no_frontmatter(self):
        md = "# Just a heading\nSome text."
        assert extract_acl_from_markdown(md, "file.md") == []

    def test_no_acl_in_frontmatter(self):
        md = "---\ntitle: Hello\n---\n# Content"
        assert extract_acl_from_markdown(md, "file.md") == []


# ── Integration with RuleResolver ────────────────────────────────────

class TestInlineRulesInEngine:

    def _make_resolver(self):
        policy = AclPolicy(
            roles={"editor": ["bob"], "viewer": ["dave"]},
            rules=[
                # Global: editor can read+write everything
                AccessRule.allow("**/*", Permission.READ | Permission.WRITE,
                                 roles=["editor"], priority=50),
                # Global: viewer can read everything
                AccessRule.allow("**/*", Permission.READ,
                                 roles=["viewer"], priority=10),
            ],
            default_deny=True,
        )
        return RuleResolver(policy)

    def test_inline_allow_overrides_global_deny(self):
        """dave (viewer) can't write globally, but inline rule grants write."""
        resolver = self._make_resolver()

        # Without inline: dave can't write
        assert resolver.can("dave", "projects/plan.md", Permission.WRITE) is False

        # Register inline rule from frontmatter: dave can write this file
        inline = [AccessRule.allow("projects/plan.md", Permission.WRITE,
                                   users=["dave"], priority=200)]
        resolver.register_inline_rules("projects/plan.md", inline)

        assert resolver.can("dave", "projects/plan.md", Permission.WRITE) is True
        # Other files still denied
        assert resolver.can("dave", "projects/other.md", Permission.WRITE) is False

    def test_inline_deny_overrides_global_allow(self):
        """bob (editor) can write globally, but inline deny blocks write."""
        resolver = self._make_resolver()

        assert resolver.can("bob", "docs/readonly.md", Permission.WRITE) is True

        inline = [AccessRule.deny_rule("docs/readonly.md", Permission.WRITE,
                                       roles=["editor"], priority=200)]
        resolver.register_inline_rules("docs/readonly.md", inline)

        assert resolver.can("bob", "docs/readonly.md", Permission.WRITE) is False
        assert resolver.can("bob", "docs/readonly.md", Permission.READ) is True

    def test_clear_inline_rules(self):
        resolver = self._make_resolver()
        inline = [AccessRule.allow("x.md", Permission.DELETE,
                                   users=["dave"], priority=200)]
        resolver.register_inline_rules("x.md", inline)
        assert resolver.can("dave", "x.md", Permission.DELETE) is True

        resolver.clear_inline_rules("x.md")
        assert resolver.can("dave", "x.md", Permission.DELETE) is False

    def test_end_to_end_with_frontmatter_parser(self):
        """Full pipeline: markdown → parse → register → check."""
        resolver = self._make_resolver()

        md = """---
title: Shared Doc
acl:
  - users: [dave]
    permissions: [read, write, delete]
  - roles: [editor]
    permissions: [delete]
    deny: true
---
# Content
"""
        rules = extract_acl_from_markdown(md, "shared/doc.md")
        resolver.register_inline_rules("shared/doc.md", rules)

        # dave gets personal read+write+delete
        assert resolver.can("dave", "shared/doc.md", Permission.READ) is True
        assert resolver.can("dave", "shared/doc.md", Permission.WRITE) is True
        assert resolver.can("dave", "shared/doc.md", Permission.DELETE) is True

        # bob (editor) can read+write (global), but inline denies delete
        assert resolver.can("bob", "shared/doc.md", Permission.READ) is True
        assert resolver.can("bob", "shared/doc.md", Permission.WRITE) is True
        assert resolver.can("bob", "shared/doc.md", Permission.DELETE) is False
