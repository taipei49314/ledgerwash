"""Remote CI replay of the original suite against the frozen PR2 judge."""
from tests.redteam.replay import replay


def test_frozen_redteam_controls_and_raw_replay(tmp_path):
    result = replay(tmp_path / "out", tmp_path / "work")
    assert result["passed"], result["problems"]
    assert result["original_case_count"] == 21
    assert result["baseline_pass"] == 17
    assert result["baseline_block"] == 4
    shell = next(item for item in result["cases"] if item["case"] == "A12-VACUOUS-LEDGER")
    assert shell["judges"]["baseline"]["findings"] == []
    assert shell["judges"]["baseline"]["residuals"] == []
