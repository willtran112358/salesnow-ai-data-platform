"""Unit tests for the Japanese / multi-language content validator."""

from src.quality.language_validator import (
    analyze_text,
    validate_for_japanese_ui,
)


def test_valid_japanese_passes() -> None:
    text = "株式会社SalesNowは企業データを提供します。"
    report = analyze_text(text)
    assert report.has_japanese
    assert report.detected_primary == "japanese"
    assert validate_for_japanese_ui(text) == []


def test_latin_only_fails_when_japanese_required() -> None:
    errors = validate_for_japanese_ui("SalesNow provides data", require_japanese=True)
    assert any("no Japanese" in e for e in errors)


def test_latin_only_allowed_when_not_required() -> None:
    errors = validate_for_japanese_ui("SalesNow provides data", require_japanese=False)
    assert errors == []


def test_empty_content_fails() -> None:
    assert validate_for_japanese_ui("") == ["empty content"]


def test_mojibake_detected() -> None:
    report = analyze_text("\ufffd\ufffd\ufffd corrupted")
    assert report.is_mojibake_suspect
    assert "mojibake / encoding corruption suspected" in validate_for_japanese_ui(
        "\ufffd\ufffd\ufffd corrupted"
    )
