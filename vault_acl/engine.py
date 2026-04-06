"""Pattern matching and rule resolution engine for Vault ACL."""
from __future__ import annotations

import fnmatch
from typing import Iterable

from interfaces.vault_acl import BaseAccessResolver
from .models import AccessRule, AclPolicy, Permission, UserIdentity

# Default priority for rules synthesised from approved grants.
# Higher than inline (200) so grants always apply unless admin overrides.
GRANT_PRIORITY = 250


class RuleResolver(BaseAccessResolver):
    """Core ACL engine that evaluates policies against file paths."""

    def __init__(self, policy: AclPolicy, grant_store: "GrantStore | None" = None):
        self.policy = policy
        self._grant_store = grant_store
        # Inline (frontmatter) overrides keyed by normalised file path
        self._inline_rules: dict[str, list[AccessRule]] = {}

    def _resolve_user(self, user: UserIdentity | str) -> UserIdentity:
        """Ensure we have a full UserIdentity with roles from the policy if it's a string."""
        if isinstance(user, UserIdentity):
            # Might still need to attach policy roles if not provided.
            # But normally, Gatekeeper will provide a fully resolved UserIdentity.
            if not user.roles:
                user.roles = self.policy.get_user_roles(user.username)
            return user
            
        return UserIdentity(
            username=user,
            roles=self.policy.get_user_roles(user),
        )

    def _match_path(self, pattern: str, file_path: str) -> bool:
        """Check if a file_path matches a glob pattern. 
        Uses fnmatch. Supports **/* if we normalize it a bit, or just standard fnmatch.
        For standard fnmatch, '*' matches everything. 
        Often 'folder/**' and 'folder/*' are conceptually useful.
        """
        # fnmatch standard handles * across separators by default in Python,
        # so folder/* matches folder/a/b.txt. We can just use fnmatchcase for case-insensitivity.
        # But commonly paths have uniform separators on Linux vs Windows, so we normalize.
        norm_pattern = pattern.replace('\\', '/')
        norm_path = file_path.replace('\\', '/')
        return fnmatch.fnmatchcase(norm_path.lower(), norm_pattern.lower())

    def _pattern_specificity(self, pattern: str) -> int:
        """Calculate how specific a pattern is to break ties.
        More specific patterns override more general ones.
        
        Simple heuristic:
        - Exact matches (no wildcards) are highest: 1000
        - Count the number of slashes (deeper paths are usually more specific)
        - Subtract penalties for wildcards: '*' (-10), '**' (-20)
        """
        if not ('*' in pattern or '?' in pattern or '[' in pattern):
            return 1000 + pattern.count('/') * 10
            
        score = pattern.count('/') * 10
        score -= pattern.count('*') * 10
        score -= pattern.count('**') * 10
        
        return score

    # ── Inline (frontmatter) rule management ───────────────────────────

    def register_inline_rules(self, file_path: str, rules: list[AccessRule]) -> None:
        """Register inline ACL rules parsed from a file's frontmatter.

        These rules participate in the same priority resolution as global
        policy rules but are typically given a higher base priority.
        """
        key = file_path.replace('\\', '/').lower()
        self._inline_rules[key] = list(rules)

    def clear_inline_rules(self, file_path: str | None = None) -> None:
        """Remove inline rules. If file_path is None, clear all."""
        if file_path is None:
            self._inline_rules.clear()
        else:
            self._inline_rules.pop(file_path.replace('\\', '/').lower(), None)

    # ── Rule matching ────────────────────────────────────────────────

    def _rules_for_user(
        self,
        identity: UserIdentity,
        file_path: str,
        rules: Iterable[AccessRule],
    ) -> list[AccessRule]:
        """Filter an iterable of rules to those matching user + path."""
        matched: list[AccessRule] = []
        for rule in rules:
            if not self._match_path(rule.pattern, file_path):
                continue
            applies = False
            if rule.roles and any(r in identity.roles for r in rule.roles):
                applies = True
            elif rule.users and identity.username in rule.users:
                applies = True
            if applies:
                matched.append(rule)
        return matched

    def effective_rules(self, user: UserIdentity | str, file_path: str) -> list[AccessRule]:
        """Find all rules (global + inline + grants) that apply to this user and path."""
        identity = self._resolve_user(user)
        matched = self._rules_for_user(identity, file_path, self.policy.rules)

        # Merge inline rules for this specific file
        key = file_path.replace('\\', '/').lower()
        if key in self._inline_rules:
            matched.extend(
                self._rules_for_user(identity, file_path, self._inline_rules[key])
            )

        # Merge active grants as synthetic allow rules
        if self._grant_store is not None:
            for grant in self._grant_store.active_grants_for_user(identity.username):
                norm_grant = grant.file_path.replace('\\', '/').lower()
                if norm_grant == key:
                    matched.append(AccessRule(
                        pattern=grant.file_path,
                        permissions=grant.permissions,
                        deny=False,
                        priority=GRANT_PRIORITY,
                        users=[grant.user],
                    ))

        return matched

    def resolve_permissions(self, user: UserIdentity | str, file_path: str) -> Permission:
        """Calculate the final Permission bitmask for a given user and file."""
        rules = self.effective_rules(user, file_path)
        
        # We process permissions bit-by-bit to handle fine-grained overrides
        # For each permission type (READ, WRITE, DELETE, CREATE), we find the "winning" rule
        
        final_perms = Permission.NONE
        
        # Helper to find the winning rule for a specific permission bit
        def check_bit(bit: Permission) -> bool:
            # Filter rules that actually specify this bit
            relevant_rules = [r for r in rules if bit in r.permissions]
            
            if not relevant_rules:
                return not self.policy.default_deny
                
            # Sort relevant rules to find the winner
            # Sort order: priority (asc), specificity (asc), deny (asc)
            # We want the LAST rule to be the winner, so we sort by "weakest" to "strongest"
            
            # Python's sort is stable. 
            # 1. Sort by specificity
            relevant_rules.sort(key=lambda r: self._pattern_specificity(r.pattern))
            
            # 2. Sort by priority
            relevant_rules.sort(key=lambda r: r.priority)
            
            # 3. Deny wins on ties. If two rules have same specificity and priority, deny should be considered stronger.
            # But since we just evaluate the last, let's group by tie breakers and pick explicitly,
            # or simply sort deny=True to be last.
            
            # Custom sort: max(priority, specificity, deny_flag)
            def rule_strength(r: AccessRule) -> tuple:
                return (r.priority, self._pattern_specificity(r.pattern), 1 if r.deny else 0)
                
            winner = max(relevant_rules, key=rule_strength)
            return not winner.deny

        # Check all possible individual permissions
        for perm in (Permission.READ, Permission.WRITE, Permission.DELETE, Permission.CREATE):
            if check_bit(perm):
                final_perms |= perm
                
        return final_perms

    def can(self, user: UserIdentity | str, file_path: str, action: Permission) -> bool:
        """Check if action is fully permitted."""
        effective = self.resolve_permissions(user, file_path)
        # return True if all action bits are present in effective
        return (effective & action) == action

    def filter_accessible(self, user: UserIdentity | str, paths: Iterable[str], action: Permission) -> list[str]:
        """Filter list of paths, returning only those where action is allowed."""
        return [p for p in paths if self.can(user, p, action)]
