"""Tests for PeopleRegistry — load, lookup, groups, aliases.

Uses tmp_path with stub markdown files.
"""
from vault_parser.people import (
    PeopleRegistry,
    Person,
    load_people_registry,
    enrich_registry_from_notes,
)


class TestPeopleRegistry:
    """In-memory registry operations."""

    def test_add_and_lookup(self):
        reg = PeopleRegistry()
        reg.add(Person(name="Иванов Иван", roles=["developer"]))
        assert reg.lookup("Иванов Иван") is not None
        assert reg.lookup("Иванов Иван").name == "Иванов Иван"

    def test_lookup_by_first_name(self):
        reg = PeopleRegistry()
        reg.add(Person(name="Иванов Иван"))
        result = reg.lookup("Иванов")
        assert result is not None

    def test_alias_lookup(self):
        reg = PeopleRegistry()
        reg.add(Person(name="Иванов Иван"))
        reg.add_alias("Ваня", "Иванов Иван")
        assert reg.lookup("Ваня") is not None
        assert reg.lookup("Ваня").name == "Иванов Иван"

    def test_is_person(self):
        reg = PeopleRegistry()
        reg.add(Person(name="Иванов Иван"))
        assert reg.is_person("Иванов Иван") is True
        assert reg.is_person("Какой-то документ") is False

    def test_contains(self):
        reg = PeopleRegistry()
        reg.add(Person(name="Иванов Иван"))
        assert "Иванов Иван" in reg
        assert "Неизвестный" not in reg


class TestLoadPeopleRegistry:
    """Loading from stub files in tmp_path."""

    def test_load_person(self, people_dir):
        reg = load_people_registry(people_dir)
        person = reg.lookup("Иванов Иван")
        assert person is not None
        assert "Backend разработчик" in person.roles

    def test_load_group(self, people_dir):
        reg = load_people_registry(people_dir)
        group = reg.lookup("Группа Backend")
        assert group is not None
        assert group.is_group is True

    def test_group_members(self, people_dir):
        reg = load_people_registry(people_dir)
        group = reg.lookup("Группа Backend")
        assert "Иванов Иван" in group.members

    def test_groups_for_person(self, people_dir):
        reg = load_people_registry(people_dir)
        groups = reg.groups_for_person("Иванов Иван")
        assert len(groups) >= 1
        assert any(g.group_name == "Группа Backend" for g in groups)


class TestEnrichFromNotes:
    """Discover aliases from wiki-links in note files."""

    def test_enrich_adds_alias(self, people_dir, tmp_path):
        reg = load_people_registry(people_dir)
        # Create a note with alias wiki-link
        notes_dir = tmp_path / "daily"
        notes_dir.mkdir()
        note = notes_dir / "2025-12-01.md"
        note.write_text(
            "- [ ] встреча [[Иванов Иван|Ваня]]",
            encoding="utf-8",
        )
        enrich_registry_from_notes(reg, notes_dir)
        assert reg.lookup("Ваня") is not None
        assert reg.lookup("Ваня").name == "Иванов Иван"
