"""
Company enrichment pipeline — normalize, deduplicate, and augment records.

Mirrors SalesNow's 名寄せ (entity resolution) and data enrichment flows.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompanyRecord:
    corporate_number: str | None = None
    company_name: str = ""
    prefecture: str | None = None
    address: str | None = None
    employee_count: int | None = None
    industry_code: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def normalize(self) -> CompanyRecord:
        self.company_name = normalize_company_name(self.company_name)
        if self.address:
            self.address = self.address.strip()
        if self.corporate_number:
            self.corporate_number = re.sub(r"\D", "", self.corporate_number)
        return self


def normalize_company_name(name: str) -> str:
    """Normalize Japanese company name for entity matching."""
    name = unicodedata.normalize("NFKC", name)
    for prefix in ("株式会社", "（株）", "(株)"):
        name = name.replace(prefix, "")
    return name.strip()


def enrich_record(record: CompanyRecord) -> CompanyRecord:
    """Apply enrichment rules to a company record."""
    record.normalize()

    if record.employee_count is not None:
        if record.employee_count < 50:
            record.attributes["size_segment"] = "small"
        elif record.employee_count < 300:
            record.attributes["size_segment"] = "mid"
        else:
            record.attributes["size_segment"] = "enterprise"

    if record.prefecture:
        record.attributes["region"] = _prefecture_to_region(record.prefecture)

    return record


def _prefecture_to_region(prefecture: str) -> str:
    kanto = {"東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県"}
    kansai = {"大阪府", "京都府", "兵庫県", "奈良県", "滋賀県", "和歌山県"}
    if prefecture in kanto:
        return "kanto"
    if prefecture in kansai:
        return "kansai"
    return "other"


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich a company record (demo)")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--prefecture", default="東京都")
    parser.add_argument("--employees", type=int, default=52)
    args = parser.parse_args()

    record = enrich_record(
        CompanyRecord(
            company_name=args.company,
            prefecture=args.prefecture,
            employee_count=args.employees,
            corporate_number="6011001135657",
        )
    )
    print(f"Enriched: {record.company_name}")
    print(f"  Segment: {record.attributes.get('size_segment')}")
    print(f"  Region:  {record.attributes.get('region')}")


if __name__ == "__main__":
    main()
