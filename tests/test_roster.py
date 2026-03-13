import pytest


def test_valid_roster_parses_to_cards(tmp_csv_file, sample_roster_csv):
    from gbgolf.data.roster import parse_roster_csv  # ImportError until Plan 02
    path = tmp_csv_file(sample_roster_csv)
    cards = parse_roster_csv(path)
    assert len(cards) > 0


def test_missing_column_fails(tmp_csv_file):
    from gbgolf.data.roster import parse_roster_csv
    bad_csv = "Player,Salary\nScottie Scheffler,12000\n"
    path = tmp_csv_file(bad_csv)
    with pytest.raises(ValueError, match="missing required columns"):
        parse_roster_csv(path)


def test_card_fields_populated(tmp_csv_file, sample_roster_csv):
    from gbgolf.data.roster import parse_roster_csv
    path = tmp_csv_file(sample_roster_csv)
    cards = parse_roster_csv(path)
    card = cards[0]
    assert card.player == "Scottie Scheffler"
    assert card.salary == 12000
    assert card.multiplier == 1.5
    assert card.collection == "Core"
