import json
import subprocess
import sys
import pytest


def test_pipeline_valid_input(tmp_csv_file, sample_roster_csv, sample_projections_csv, tmp_path, valid_config_dict):
    from gbgolf.data import validate_pipeline  # ImportError until Plan 04
    roster_path = tmp_csv_file(sample_roster_csv, "roster.csv")
    proj_path = tmp_csv_file(sample_projections_csv, "proj.csv")
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(valid_config_dict))
    result = validate_pipeline(roster_path, proj_path, str(config_file))
    assert len(result.valid_cards) > 0
    assert all(c.effective_value is not None for c in result.valid_cards)


def test_pipeline_exclusion_counts(tmp_csv_file, sample_roster_csv, sample_projections_csv, tmp_path, valid_config_dict):
    from gbgolf.data import validate_pipeline
    roster_path = tmp_csv_file(sample_roster_csv, "roster.csv")
    proj_path = tmp_csv_file(sample_projections_csv, "proj.csv")
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(valid_config_dict))
    result = validate_pipeline(roster_path, proj_path, str(config_file))
    # sample data has: 1 no-projection, 1 zero-salary, 1 expired — all excluded
    assert len(result.excluded) >= 3


def test_cli_valid(tmp_csv_file, sample_roster_csv, sample_projections_csv, tmp_path, valid_config_dict):
    roster_path = tmp_csv_file(sample_roster_csv, "roster.csv")
    proj_path = tmp_csv_file(sample_projections_csv, "proj.csv")
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(valid_config_dict))
    result = subprocess.run(
        [sys.executable, "-m", "gbgolf.data", "validate",
         roster_path, proj_path, "--config", str(config_file)],
        capture_output=True, text=True
    )
    assert result.returncode == 0


def test_cli_bad_roster(tmp_csv_file, tmp_path, valid_config_dict):
    bad_roster = tmp_csv_file("Player,Salary\nBad,0\n", "bad.csv")
    proj = tmp_csv_file("player,projected_score\n", "proj.csv")
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(valid_config_dict))
    result = subprocess.run(
        [sys.executable, "-m", "gbgolf.data", "validate",
         bad_roster, proj, "--config", str(config_file)],
        capture_output=True, text=True
    )
    assert result.returncode != 0
