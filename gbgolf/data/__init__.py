"""
GB Golf Optimizer data layer.
Public API: validate_pipeline(), validate_pipeline_auto(), validate_pipeline_hybrid(),
            load_cards(), load_config(), load_projections_from_db()
"""
from sqlalchemy import text

from gbgolf.data.config import load_contest_config, ContestConfig
from gbgolf.data.filters import apply_filters
from gbgolf.data.matching import match_projections, normalize_name
from gbgolf.data.models import Card, ExclusionRecord, ValidationResult
from gbgolf.data.projections import parse_projections_csv
from gbgolf.data.roster import parse_roster_csv
from gbgolf.db import db


def load_cards(roster_path: str, projections_path: str) -> tuple[list[Card], list[str]]:
    """
    Parse and enrich cards from CSV files.
    Returns (enriched_cards, projection_warnings).
    enriched_cards have projected_score and effective_value set (or None if unmatched).
    """
    cards = parse_roster_csv(roster_path)
    projections, warnings = parse_projections_csv(projections_path)
    enriched = match_projections(cards, projections)
    return enriched, warnings


def load_config(config_path: str) -> list[ContestConfig]:
    """Load and validate contest config JSON. Returns list of ContestConfig."""
    return load_contest_config(config_path)


def validate_pipeline(
    roster_path: str,
    projections_path: str,
    config_path: str,
) -> ValidationResult:
    """
    Full validation pipeline: parse -> enrich -> filter.
    Raises ValueError if the valid card pool is too small for the smallest contest.
    """
    enriched, warnings = load_cards(roster_path, projections_path)
    contests = load_config(config_path)

    valid_cards, excluded = apply_filters(enriched)

    # Guard: fail before Phase 2 receives an unusable pool
    if contests:
        min_required = min(c.roster_size for c in contests)
        if len(valid_cards) < min_required:
            raise ValueError(
                f"Only {len(valid_cards)} valid card(s) found — "
                f"smallest contest requires at least {min_required}. "
                f"Check your exclusion report."
            )

    return ValidationResult(
        valid_cards=valid_cards,
        excluded=excluded,
        projection_warnings=warnings,
    )


def load_projections_from_db() -> dict[str, float]:
    """Load latest projections from DB. Returns {normalized_name: score}.

    Raises ValueError if no projections exist in the database.
    """
    row = db.session.execute(
        text("SELECT id FROM fetches ORDER BY fetched_at DESC LIMIT 1")
    ).mappings().fetchone()
    if row is None:
        raise ValueError("No projections available \u2014 please upload a CSV")

    fetch_id = row["id"]
    rows = db.session.execute(
        text("SELECT player_name, projected_score FROM projections WHERE fetch_id = :fid"),
        {"fid": fetch_id},
    ).mappings().all()

    return {normalize_name(r["player_name"]): r["projected_score"] for r in rows}


def validate_pipeline_auto(roster_path: str, config_path: str) -> ValidationResult:
    """Validation pipeline using DB projections instead of CSV file.

    Identical to validate_pipeline() except projections come from the database
    via load_projections_from_db() instead of a CSV file path.
    """
    cards = parse_roster_csv(roster_path)
    projections = load_projections_from_db()
    enriched = match_projections(cards, projections)
    contests = load_config(config_path)

    valid_cards, excluded = apply_filters(enriched)

    if contests:
        min_required = min(c.roster_size for c in contests)
        if len(valid_cards) < min_required:
            raise ValueError(
                f"Only {len(valid_cards)} valid card(s) found \u2014 "
                f"smallest contest requires at least {min_required}. "
                f"Check your exclusion report."
            )

    return ValidationResult(
        valid_cards=valid_cards,
        excluded=excluded,
        projection_warnings=[],
    )


def validate_pipeline_hybrid(
    roster_path: str,
    projections_path: str,
    config_path: str,
) -> ValidationResult:
    """Validation pipeline merging CSV projections (priority) with DB projections (fallback).

    CSV projections overwrite DB projections on name conflict. Players missing
    from both sources get projected_score=None and are filtered out by apply_filters.
    """
    cards = parse_roster_csv(roster_path)
    csv_projections, warnings = parse_projections_csv(projections_path)

    try:
        db_projections = load_projections_from_db()
    except ValueError:
        db_projections = {}

    # Merge: DB first, then CSV overwrites — gives CSV priority
    merged = {**db_projections, **csv_projections}

    enriched = match_projections(cards, merged)
    contests = load_config(config_path)

    valid_cards, excluded = apply_filters(enriched)

    if contests:
        min_required = min(c.roster_size for c in contests)
        if len(valid_cards) < min_required:
            raise ValueError(
                f"Only {len(valid_cards)} valid card(s) found — "
                f"smallest contest requires at least {min_required}. "
                f"Check your exclusion report."
            )

    return ValidationResult(
        valid_cards=valid_cards,
        excluded=excluded,
        projection_warnings=warnings,
    )


__all__ = [
    "validate_pipeline",
    "validate_pipeline_auto",
    "validate_pipeline_hybrid",
    "load_cards",
    "load_config",
    "load_projections_from_db",
    "Card",
    "ContestConfig",
    "ExclusionRecord",
    "ValidationResult",
    "normalize_name",
]
