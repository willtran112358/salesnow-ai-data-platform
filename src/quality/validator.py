"""
Data quality validator for company records.

Implements completeness, format, and business rule checks aligned with SalesNow SLAs.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    total: int = 0
    passed: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def ok(self) -> bool:
        return self.pass_rate >= 0.995


class CompanyRecordValidator:
    CORPORATE_NUMBER_PATTERN = re.compile(r"^\d{13}$")
    POSTAL_CODE_PATTERN = re.compile(r"^\d{3}-?\d{4}$")

    def validate_record(self, record: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        if not record.get("company_name"):
            errors.append("company_name is required")

        corp_num = record.get("corporate_number")
        if corp_num and not self.CORPORATE_NUMBER_PATTERN.match(str(corp_num)):
            errors.append(f"invalid corporate_number: {corp_num}")

        postal = record.get("postal_code")
        if postal and not self.POSTAL_CODE_PATTERN.match(str(postal)):
            errors.append(f"invalid postal_code: {postal}")

        employees = record.get("employee_count")
        if employees is not None and (not isinstance(employees, int) or employees < 0):
            errors.append("employee_count must be a non-negative integer")

        return errors

    def validate_batch(self, records: list[dict[str, Any]]) -> ValidationResult:
        result = ValidationResult(total=len(records))
        for i, record in enumerate(records):
            errors = self.validate_record(record)
            if errors:
                result.failures.append({"index": i, "errors": errors})
            else:
                result.passed += 1
        return result


SAMPLE_RECORDS = [
    {
        "company_name": "株式会社SalesNow",
        "corporate_number": "6011001135657",
        "postal_code": "150-0031",
        "employee_count": 52,
        "prefecture": "東京都",
    },
    {
        "company_name": "パナソニック株式会社",
        "corporate_number": "1234567890123",
        "employee_count": 240000,
    },
    {
        "company_name": "",
        "corporate_number": "INVALID",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="sample", choices=["sample"])
    args = parser.parse_args()

    records = SAMPLE_RECORDS if args.dataset == "sample" else []
    result = CompanyRecordValidator().validate_batch(records)

    print(f"Validated {result.total} records")
    print(f"Pass rate: {result.pass_rate:.1%}")
    print(f"SLA met:   {result.ok}")

    for failure in result.failures:
        print(f"  FAIL [{failure['index']}]: {failure['errors']}")


if __name__ == "__main__":
    main()
