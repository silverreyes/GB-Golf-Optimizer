import pytest


def test_normalize_lowercase():
    from gbgolf.data.matching import normalize_name  # ImportError until Plan 02
    assert normalize_name("Scottie Scheffler") == "scottie scheffler"


def test_normalize_strips_whitespace():
    from gbgolf.data.matching import normalize_name
    assert normalize_name("  Rory McIlroy  ") == "rory mcilroy"


def test_normalize_accent_decomposition():
    from gbgolf.data.matching import normalize_name
    assert normalize_name("Ludvig \u00c5berg") == normalize_name("Ludvig Aberg")


def test_effective_value_calculated(tmp_csv_file, sample_roster_csv, sample_projections_csv):
    from gbgolf.data.matching import match_projections
    from gbgolf.data.roster import parse_roster_csv
    from gbgolf.data.projections import parse_projections_csv
    roster_path = tmp_csv_file(sample_roster_csv, "roster.csv")
    proj_path = tmp_csv_file(sample_projections_csv, "proj.csv")
    cards = parse_roster_csv(roster_path)
    projections, _ = parse_projections_csv(proj_path)
    enriched = match_projections(cards, projections)
    scheffler = next(c for c in enriched if c.player == "Scottie Scheffler")
    assert scheffler.projected_score == 72.5
    assert scheffler.effective_value == pytest.approx(72.5 * 1.5)


def test_unmatched_card_has_no_projection(tmp_csv_file, sample_roster_csv, sample_projections_csv):
    from gbgolf.data.matching import match_projections
    from gbgolf.data.roster import parse_roster_csv
    from gbgolf.data.projections import parse_projections_csv
    roster_path = tmp_csv_file(sample_roster_csv, "roster.csv")
    proj_path = tmp_csv_file(sample_projections_csv, "proj.csv")
    cards = parse_roster_csv(roster_path)
    projections, _ = parse_projections_csv(proj_path)
    enriched = match_projections(cards, projections)
    no_match = next(c for c in enriched if c.player == "No Projection Guy")
    assert no_match.projected_score is None
