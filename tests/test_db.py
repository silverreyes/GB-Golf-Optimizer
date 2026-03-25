"""Tests for database schema (FETCH-05)."""
from datetime import datetime, UTC

from sqlalchemy import text


def test_fetches_table_exists(db_session):
    """Verify fetches table has all required columns and accepts valid data."""
    db_session.execute(text("""
        INSERT INTO fetches (tournament_name, fetched_at, player_count, source, tour)
        VALUES (:tn, :fa, :pc, :src, :tour)
    """), {"tn": "Test Open", "fa": datetime.now(UTC), "pc": 10, "src": "datagolf", "tour": "pga"})
    db_session.commit()
    row = db_session.execute(
        text("SELECT * FROM fetches WHERE tournament_name = 'Test Open'")
    ).mappings().one()
    assert row["tournament_name"] == "Test Open"
    assert row["player_count"] == 10
    assert row["source"] == "datagolf"
    assert row["tour"] == "pga"


def test_projections_table_exists(db_session):
    """Verify projections table with FK to fetches."""
    db_session.execute(text("""
        INSERT INTO fetches (tournament_name, fetched_at, player_count, source, tour)
        VALUES (:tn, :fa, :pc, :src, :tour)
    """), {"tn": "Test Open", "fa": datetime.now(UTC), "pc": 1, "src": "datagolf", "tour": "pga"})
    fetch_id = db_session.execute(text("SELECT id FROM fetches")).scalar_one()
    db_session.execute(text("""
        INSERT INTO projections (fetch_id, player_name, projected_score)
        VALUES (:fid, :pn, :ps)
    """), {"fid": fetch_id, "pn": "Scottie Scheffler", "ps": 68.5})
    db_session.commit()
    row = db_session.execute(
        text("SELECT * FROM projections WHERE player_name = 'Scottie Scheffler'")
    ).mappings().one()
    assert row["player_name"] == "Scottie Scheffler"
    assert abs(row["projected_score"] - 68.5) < 0.01


def test_projections_fk_constraint(db_session):
    """FK constraint rejects invalid fetch_id."""
    import pytest
    # SQLite does not enforce FK constraints by default -- enable them
    db_session.execute(text("PRAGMA foreign_keys = ON"))
    with pytest.raises(Exception):  # IntegrityError on PostgreSQL, OperationalError on SQLite with FK on
        db_session.execute(text("""
            INSERT INTO projections (fetch_id, player_name, projected_score)
            VALUES (99999, 'Ghost Player', 70.0)
        """))
        db_session.commit()


def test_cascade_delete(db_session):
    """Deleting a fetches row cascades to its projections."""
    db_session.execute(text("PRAGMA foreign_keys = ON"))
    db_session.execute(text("""
        INSERT INTO fetches (tournament_name, fetched_at, player_count, source, tour)
        VALUES (:tn, :fa, :pc, :src, :tour)
    """), {"tn": "Cascade Test", "fa": datetime.now(UTC), "pc": 2, "src": "datagolf", "tour": "pga"})
    fetch_id = db_session.execute(text("SELECT id FROM fetches")).scalar_one()
    for name in ["Player A", "Player B"]:
        db_session.execute(text("""
            INSERT INTO projections (fetch_id, player_name, projected_score)
            VALUES (:fid, :pn, :ps)
        """), {"fid": fetch_id, "pn": name, "ps": 70.0})
    db_session.commit()
    db_session.execute(text("DELETE FROM fetches WHERE id = :fid"), {"fid": fetch_id})
    db_session.commit()
    count = db_session.execute(
        text("SELECT COUNT(*) FROM projections WHERE fetch_id = :fid"),
        {"fid": fetch_id},
    ).scalar_one()
    assert count == 0


def test_fetches_columns_not_nullable(db_session):
    """NOT NULL constraint on fetches.tournament_name."""
    import pytest
    with pytest.raises(Exception):
        db_session.execute(text("""
            INSERT INTO fetches (tournament_name, fetched_at, player_count, source, tour)
            VALUES (NULL, :fa, :pc, :src, :tour)
        """), {"fa": datetime.now(UTC), "pc": 10, "src": "datagolf", "tour": "pga"})
        db_session.commit()
