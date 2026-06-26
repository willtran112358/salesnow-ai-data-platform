"""
Multi-language / Japanese content validator.

Per the 2026-06-26 product/CEO discussion: crawled text is ultimately shown to
Japanese end users, so AI-bound content (summaries, descriptions, hook talks)
must be language-validated before it reaches the final / AI feature layer.

This guards against:
  - Garbled or mojibake text from crawl encoding issues
  - Non-Japanese content leaking into Japanese-facing fields
  - Empty / placeholder strings being fed to the LLM scoring & embedding stage

Dependency-free: uses Unicode block ranges so it runs inside any Spark/UDF
or Airflow task without extra libraries.
"""

from __future__ import annotations

import argparse
import unicodedata
from dataclasses import dataclass

# Unicode ranges relevant to Japanese text
_HIRAGANA = (0x3040, 0x309F)
_KATAKANA = (0x30A0, 0x30FF)
_KANJI = (0x4E00, 0x9FFF)
_FULLWIDTH = (0xFF00, 0xFFEF)


def _in_range(cp: int, rng: tuple[int, int]) -> bool:
    return rng[0] <= cp <= rng[1]


@dataclass
class LanguageReport:
    text_length: int
    japanese_ratio: float
    has_japanese: bool
    is_mojibake_suspect: bool
    detected_primary: str

    @property
    def ok_for_japanese_ui(self) -> bool:
        """Content is safe to show to Japanese users in AI features."""
        return (
            self.text_length > 0
            and not self.is_mojibake_suspect
            and (self.has_japanese or self.detected_primary == "latin")
        )


def analyze_text(text: str) -> LanguageReport:
    """Analyze a string for Japanese suitability before AI ingestion."""
    if not text:
        return LanguageReport(0, 0.0, False, False, "empty")

    normalized = unicodedata.normalize("NFKC", text)
    jp_chars = 0
    latin_chars = 0
    replacement_chars = 0

    for ch in text:
        cp = ord(ch)
        if ch == "\ufffd":  # Unicode replacement char -> encoding broke
            replacement_chars += 1
        if (
            _in_range(cp, _HIRAGANA)
            or _in_range(cp, _KATAKANA)
            or _in_range(cp, _KANJI)
            or _in_range(cp, _FULLWIDTH)
        ):
            jp_chars += 1
        elif ch.isalpha() and cp < 0x250:
            latin_chars += 1

    meaningful = max(jp_chars + latin_chars, 1)
    jp_ratio = jp_chars / meaningful
    has_jp = jp_chars > 0
    mojibake = replacement_chars > 0 or _looks_like_mojibake(normalized)

    if has_jp:
        primary = "japanese"
    elif latin_chars > 0:
        primary = "latin"
    else:
        primary = "unknown"

    return LanguageReport(
        text_length=len(text),
        japanese_ratio=round(jp_ratio, 3),
        has_japanese=has_jp,
        is_mojibake_suspect=mojibake,
        detected_primary=primary,
    )


def _looks_like_mojibake(text: str) -> bool:
    """Heuristic: clusters of Latin-1 supplement symbols often signal mojibake."""
    suspect = sum(1 for ch in text if 0x80 <= ord(ch) <= 0xBF)
    return suspect >= 3 and suspect / max(len(text), 1) > 0.2


def validate_for_japanese_ui(text: str, *, require_japanese: bool = True) -> list[str]:
    """Return a list of validation errors for Japanese-facing AI content."""
    report = analyze_text(text)
    errors: list[str] = []

    if report.text_length == 0:
        errors.append("empty content")
        return errors
    if report.is_mojibake_suspect:
        errors.append("mojibake / encoding corruption suspected")
    if require_japanese and not report.has_japanese:
        errors.append(
            f"no Japanese characters found (primary={report.detected_primary})"
        )
    return errors


_SAMPLES = [
    "株式会社SalesNowは企業データを提供します。",  # valid Japanese
    "SalesNow provides corporate data.",  # latin (allowed if require_japanese=False)
    "æ ªå¼ä¼šç¤¾",  # mojibake-ish
    "",  # empty
]


def main() -> None:
    # Ensure Japanese output prints on consoles with non-UTF-8 default encoding.
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Japanese content validator (demo)")
    parser.add_argument("--text", help="Text to validate")
    parser.add_argument("--allow-latin", action="store_true")
    args = parser.parse_args()

    texts = [args.text] if args.text else _SAMPLES
    for t in texts:
        report = analyze_text(t)
        errors = validate_for_japanese_ui(t, require_japanese=not args.allow_latin)
        status = "PASS" if not errors else "FAIL"
        preview = (t[:30] + "...") if len(t) > 30 else t
        print(f"[{status}] '{preview}'")
        print(
            f"   primary={report.detected_primary} jp_ratio={report.japanese_ratio} "
            f"mojibake={report.is_mojibake_suspect}"
        )
        if errors:
            print(f"   errors: {errors}")


if __name__ == "__main__":
    main()
