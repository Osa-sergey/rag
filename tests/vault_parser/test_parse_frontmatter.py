"""Tests for parse_frontmatter and sleep/energy extraction."""
from vault_parser.parser import parse_frontmatter, _extract_sleep_data, _extract_energy_data


class TestParseFrontmatter:
    """YAML frontmatter splitting."""

    def test_valid_frontmatter(self):
        text = "---\nkey: value\ntags: [a, b]\n---\nBody text here"
        fm, body = parse_frontmatter(text)
        assert fm == {"key": "value", "tags": ["a", "b"]}
        assert body == "Body text here"

    def test_no_frontmatter(self):
        text = "Just plain markdown text"
        fm, body = parse_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_empty_frontmatter(self):
        text = "---\n---\nBody"
        fm, body = parse_frontmatter(text)
        assert fm == {}
        assert body == "Body"

    def test_invalid_yaml(self):
        text = "---\n: : [broken\n---\nBody"
        fm, body = parse_frontmatter(text)
        assert fm == {}

    def test_multiline_body_preserved(self):
        text = "---\nk: v\n---\nLine 1\nLine 2\nLine 3"
        fm, body = parse_frontmatter(text)
        assert "Line 1" in body
        assert "Line 3" in body


class TestExtractSleepData:
    """SleepData from frontmatter dict."""

    def test_full_sleep_data(self):
        fm = {
            "bed-time-start": "23:00",
            "sleep-start": "23:30",
            "sleep-end": "6:00",
            "sleep-duration": "6:30",
            "sleep-quality": 7,
            "quick-fall-asleep": True,
            "night-awakenings": False,
            "deep-sleep": True,
            "remembered-dreams": False,
            "no-nightmare": True,
            "morning-mood": 6,
            "no-phone": True,
            "physical-exercise": False,
            "late-dinner": True,
        }
        sd = _extract_sleep_data(fm)
        assert sd.bed_time_start == "23:00"
        assert sd.sleep_quality == 7
        assert sd.quick_fall_asleep is True
        assert sd.night_awakenings is False
        assert sd.deep_sleep is True
        assert sd.morning_mood == 6
        assert sd.late_dinner is True
        assert sd.physical_exercise is False

    def test_sexagesimal_duration(self):
        """YAML parses 6:30 as int 390 (sexagesimal). Parser converts back."""
        fm = {"sleep-duration": 390}  # 6*60+30
        sd = _extract_sleep_data(fm)
        assert sd.sleep_duration == "6:30"

    def test_empty_frontmatter(self):
        sd = _extract_sleep_data({})
        assert sd.sleep_quality is None
        assert sd.bed_time_start is None
        assert sd.quick_fall_asleep is False

    def test_russian_boolean(self):
        fm = {"quick-fall-asleep": "да"}
        sd = _extract_sleep_data(fm)
        assert sd.quick_fall_asleep is True


class TestExtractEnergyData:
    """EnergyData from frontmatter dict."""

    def test_full_energy(self):
        fm = {"morning-energy": 6, "day-energy": 7, "evening-energy": 5}
        ed = _extract_energy_data(fm)
        assert ed.morning_energy == 6
        assert ed.day_energy == 7
        assert ed.evening_energy == 5
        assert ed.average() == 6.0

    def test_partial_energy(self):
        fm = {"morning-energy": 8}
        ed = _extract_energy_data(fm)
        assert ed.morning_energy == 8
        assert ed.day_energy is None

    def test_empty(self):
        ed = _extract_energy_data({})
        assert ed.morning_energy is None
        assert ed.average() is None
