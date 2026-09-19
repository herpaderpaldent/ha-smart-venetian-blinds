"""Tests for the season boundary option values and labels."""

from __future__ import annotations

import pytest

from custom_components.smart_venetian_blinds.season import (
    day_choices,
    format_day,
    normalize_language,
    parse_day_value,
    to_day_value,
)


@pytest.mark.unit
class TestDayChoices:
    """Tests for the option list offered by the form and the select entities."""

    def test_covers_every_day_including_the_leap_day(self) -> None:
        """All 366 boundaries are offered, so 29 February stays selectable."""
        values = [value for value, _ in day_choices()]

        assert len(values) == 366
        assert values[0] == "01-01"
        assert values[-1] == "12-31"
        assert "02-29" in values

    def test_values_are_language_independent(self) -> None:
        """Only the labels are localized; the stored values never change."""
        english = [value for value, _ in day_choices("en")]
        german = [value for value, _ in day_choices("de")]

        assert english == german

    def test_labels_are_localized(self) -> None:
        """Each language renders its own month names and punctuation."""
        labels_en = dict(day_choices("en"))
        labels_de = dict(day_choices("de"))

        assert labels_en["03-15"] == "15 March"
        assert labels_de["03-15"] == "15. März"

    def test_labels_are_unique(self) -> None:
        """The select entity maps a label back to a value, so labels must not collide."""
        for language in ("en", "de"):
            labels = [label for _, label in day_choices(language)]
            assert len(set(labels)) == len(labels)


@pytest.mark.unit
class TestLanguageHandling:
    """Tests for reducing a Home Assistant language tag to a known one."""

    @pytest.mark.parametrize(
        ("language", "expected"),
        [("de", "de"), ("de-CH", "de"), ("de_DE", "de"), ("en", "en"), ("fr", "en"), (None, "en"), ("", "en")],
    )
    def test_normalize(self, language: str | None, expected: str) -> None:
        """Regional variants resolve to their base language, unknown ones to English."""
        assert normalize_language(language) == expected

    def test_unknown_language_still_formats(self) -> None:
        """An unsupported language falls back rather than raising."""
        assert format_day(3, 15, "fr") == "15 March"


@pytest.mark.unit
class TestValueRoundTrip:
    """Tests for the MM-DD value format."""

    def test_round_trip(self) -> None:
        """A stored value parses back to the same month and day."""
        assert parse_day_value(to_day_value(3, 15)) == (3, 15)
        assert parse_day_value("02-29") == (2, 29)

    @pytest.mark.parametrize("value", ["02-30", "13-01", "00-10", "not-a-day", "", "3-15-2026"])
    def test_rejects_impossible_values(self, value: str) -> None:
        """Anything the dropdown cannot have produced is rejected."""
        with pytest.raises(ValueError, match=".*"):
            parse_day_value(value)
