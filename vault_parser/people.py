"""People registry — loads person & group data from the vault ``people/`` directory.

Provides a lookup table for matching wiki-links to real people vs generic note links.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Wiki-link inside YAML or markdown: [[Target|Alias]] or [[Target]]
_WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

# Markdown table row: | [[Person]] | role description |
_TABLE_ROW_RE = re.compile(
    r"\|\s*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]\s*\|\s*(.+?)\s*\|"
)


@dataclass
class GroupMembership:
    """A person's membership in a group."""
    group_name: str
    role: str


@dataclass
class Person:
    """A single person from the vault."""
    name: str                               # canonical name (filename stem)
    roles: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    telegram: str | None = None
    source_file: Path | None = None
    is_group: bool = False                  # True for "Группа ..." files
    members: dict[str, str] = field(default_factory=dict)  # for groups: {member_name: role}

    @property
    def first_name(self) -> str:
        """Return first word of the name (usually the first name or group prefix)."""
        parts = self.name.split()
        return parts[-1] if len(parts) == 2 else parts[0]


@dataclass
class PeopleRegistry:
    """Registry of all people and groups from the vault.

    Used to distinguish real person mentions from generic wiki-links.
    """
    people: dict[str, Person] = field(default_factory=dict)  # name -> Person
    _alias_map: dict[str, str] = field(default_factory=dict)  # lowercase alias -> canonical name

    def add(self, person: Person) -> None:
        """Register a person and index all name variations."""
        self.people[person.name] = person

        # Index: full name (always overwrites — canonical name has highest priority)
        self._alias_map[person.name.lower()] = person.name

        # Index: parts of the name (first name, last name separately)
        # Don't overwrite existing entries — a full-name match takes priority
        # e.g. "Аня" as a standalone person should not be overwritten by
        #       "Аня" as a part of "Буздалина Аня"
        for part in person.name.split():
            if len(part) >= 2:
                key = part.lower()
                if key not in self._alias_map:
                    self._alias_map[key] = person.name

    def add_alias(self, alias: str, canonical_name: str) -> None:
        """Register an additional alias for a person."""
        self._alias_map[alias.lower()] = canonical_name

    def lookup(self, name_or_alias: str) -> Person | None:
        """Find a person by exact name, alias, or name part.

        Matches against: full name, first name, last name, and all
        aliases discovered from wiki-links in notes.
        """
        key = name_or_alias.lower().strip()

        # Exact alias match (includes full names, name parts, and discovered aliases)
        canonical = self._alias_map.get(key)
        if canonical:
            return self.people.get(canonical)

        return None

    def is_person(self, wiki_target: str) -> bool:
        """Check if a wiki-link target refers to a known person or group."""
        return self.lookup(wiki_target) is not None

    def all_names(self) -> list[str]:
        """Return all canonical person names."""
        return list(self.people.keys())

    def all_groups(self) -> list[Person]:
        """Return all group entries."""
        return [p for p in self.people.values() if p.is_group]

    def all_persons(self) -> list[Person]:
        """Return all individual (non-group) entries."""
        return [p for p in self.people.values() if not p.is_group]

    def groups_for_person(self, name_or_alias: str) -> list[GroupMembership]:
        """Find all groups that a person belongs to.

        Args:
            name_or_alias: Person name or alias.

        Returns:
            List of GroupMembership(group_name, role) for each group.
        """
        person = self.lookup(name_or_alias)
        if not person:
            return []

        canonical = person.name
        result = []
        for group in self.all_groups():
            if canonical in group.members:
                result.append(GroupMembership(
                    group_name=group.name,
                    role=group.members[canonical],
                ))
        return result

    def __len__(self) -> int:
        return len(self.people)

    def __contains__(self, name: str) -> bool:
        return self.is_person(name)


def _parse_person_file(file_path: Path) -> Person:
    """Parse a single person or group markdown file."""
    text = file_path.read_text(encoding="utf-8")
    name = file_path.stem
    is_group = name.lower().startswith("группа")

    person = Person(
        name=name,
        source_file=file_path,
        is_group=is_group,
    )

    # Parse YAML frontmatter (person files)
    if text.strip().startswith("---"):
        end_idx = text.find("\n---", 3)
        if end_idx != -1:
            fm_raw = text[3:end_idx].strip()
            body = text[end_idx + 4:].strip()
            try:
                fm = yaml.safe_load(fm_raw)
                if isinstance(fm, dict):
                    # Roles — clean wiki-link syntax
                    raw_roles = fm.get("roles", [])
                    if isinstance(raw_roles, list):
                        for r in raw_roles:
                            r_str = str(r)
                            # Extract display text from [[target|alias]]
                            m = _WIKI_LINK_RE.search(r_str)
                            if m:
                                person.roles.append(m.group(2) or m.group(1))
                            else:
                                person.roles.append(r_str.strip())

                    # Interests — clean wiki-link syntax
                    raw_interests = fm.get("interests", [])
                    if isinstance(raw_interests, list):
                        for i in raw_interests:
                            i_str = str(i)
                            m = _WIKI_LINK_RE.search(i_str)
                            if m:
                                person.interests.append(m.group(2) or m.group(1))
                            else:
                                person.interests.append(i_str.strip())

                    person.telegram = fm.get("tg")
            except yaml.YAMLError:
                pass
        else:
            body = text
    else:
        body = text

    # Parse group tables: extract [[Member]] links with roles from "Что" column
    if is_group:
        for line in body.split("\n"):
            m = _TABLE_ROW_RE.match(line.strip())
            if m:
                member_name = m.group(1).strip()
                role = m.group(2).strip()
                if not member_name.lower().startswith("группа"):
                    person.members[member_name] = role

    return person


def load_people_registry(people_dir: str | Path) -> PeopleRegistry:
    """Load all people and groups from the vault ``people/`` directory.

    Args:
        people_dir: Path to the ``people/`` directory.

    Returns:
        Populated PeopleRegistry.
    """
    people_dir = Path(people_dir)
    registry = PeopleRegistry()

    if not people_dir.exists():
        logger.warning("People directory not found: %s", people_dir)
        return registry

    for f in sorted(people_dir.glob("*.md")):
        person = _parse_person_file(f)
        registry.add(person)

    # Scan all daily notes for aliases used in wiki-links like [[Котиков Федор|Федей]]
    # We collect these from the people files' references in other notes
    # For now, register common Russian name declensions by scanning the people dir
    logger.info("Loaded %d people entries from %s", len(registry), people_dir)
    return registry


def enrich_registry_from_notes(
    registry: PeopleRegistry,
    notes_dir: str | Path,
) -> None:
    """Scan note files to discover wiki-link aliases and add them to the registry.

    When notes use ``[[Котиков Федор|Федей]]``, this registers "Федей" → "Котиков Федор".
    """
    notes_dir = Path(notes_dir)
    if not notes_dir.exists():
        return

    alias_count = 0
    for md_file in notes_dir.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for m in _WIKI_LINK_RE.finditer(text):
            target = m.group(1).strip()
            alias = m.group(2).strip() if m.group(2) else None

            # Only register if target is a known person
            if alias and registry.is_person(target):
                registry.add_alias(alias, target)
                alias_count += 1

    if alias_count:
        logger.info("Discovered %d additional aliases from notes", alias_count)
