"""Unit tests for data quality validator."""

from src.quality.validator import CompanyRecordValidator


def test_valid_record_passes() -> None:
    validator = CompanyRecordValidator()
    errors = validator.validate_record(
        {
            "company_name": "株式会社SalesNow",
            "corporate_number": "6011001135657",
            "postal_code": "150-0031",
            "employee_count": 52,
        }
    )
    assert errors == []


def test_invalid_corporate_number() -> None:
    validator = CompanyRecordValidator()
    errors = validator.validate_record(
        {"company_name": "Test Co", "corporate_number": "INVALID"}
    )
    assert any("corporate_number" in e for e in errors)


def test_batch_pass_rate() -> None:
    records = [
        {"company_name": "A社", "corporate_number": "6011001135657"},
        {"company_name": "", "corporate_number": "bad"},
    ]
    result = CompanyRecordValidator().validate_batch(records)
    assert result.total == 2
    assert result.passed == 1
    assert result.pass_rate == 0.5
