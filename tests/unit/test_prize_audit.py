import pytest

from reflector.prize import audit


@pytest.mark.unit
def test_prize_audit_passes_machine_checks_and_keeps_manual_gates() -> None:
    report = audit()
    assert report.technical_ready
    assert not report.prize_ready
    assert not [item for item in report.checks if item.status == "fail"]
    assert {
        item.name for item in report.checks if item.status == "manual"
    } >= {
        "public_repository",
        "participant_eligibility",
        "kaggle_rerun",
        "public_evaluation",
        "competition_publication",
        "paper_submission",
    }
