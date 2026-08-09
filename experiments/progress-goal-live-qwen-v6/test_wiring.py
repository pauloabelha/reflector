from pathlib import Path


def test_runner_uses_generic_tracker_hook() -> None:
    text = (Path(__file__).resolve().parent / "live.py").read_text(encoding="utf-8")
    assert "RUNNER.TRACKER = TRACKER" in text
    assert "infer_roles" not in text
