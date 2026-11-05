"""Only numbered continuations belong to a session's title lineage."""
import pytest

from hermes_state import SessionDB


@pytest.fixture
def lineage_db(tmp_path):
    db = SessionDB(tmp_path / "lineage.db")
    try:
        yield db
    finally:
        db.close()


def add_session(db, session_id, title, timestamp):
    db.create_session(session_id, "cli")
    db.set_session_title(session_id, title)
    db._conn.execute("UPDATE sessions SET started_at = ? WHERE id = ?", (timestamp, session_id))
    db._conn.commit()


@pytest.mark.parametrize("suffix", ["notes", "2 notes", "2 #99", "", "-2"])
def test_resume_does_not_select_unrelated_hash_titles(lineage_db, suffix):
    add_session(lineage_db, "original", "my project", 1)
    add_session(lineage_db, "unrelated", f"my project #{suffix}", 2)
    assert lineage_db.resolve_session_by_title("my project") == "original"


def test_resume_filters_unrelated_titles_before_choosing_latest(lineage_db):
    add_session(lineage_db, "continuation", "100% [done]_ #2", 2)
    add_session(lineage_db, "unrelated", "100% [done]_ #2 #99", 3)
    assert lineage_db.resolve_session_by_title("100% [done]_") == "continuation"


def test_missing_lineage_is_not_created_by_unrelated_hash_title(lineage_db):
    add_session(lineage_db, "unrelated", "my project #notes", 2)
    assert lineage_db.resolve_session_by_title("my project") is None
    assert lineage_db.get_next_title_in_lineage("my project") == "my project"


def test_next_number_ignores_nested_numbered_titles(lineage_db):
    add_session(lineage_db, "original", "my project", 1)
    add_session(lineage_db, "continuation", "my project #2", 2)
    add_session(lineage_db, "unrelated", "my project #2 #99", 3)
    assert lineage_db.get_next_title_in_lineage("my project") == "my project #3"
    assert lineage_db.get_next_title_in_lineage("my project #2") == "my project #3"


def test_lineage_matching_keeps_case_sensitive_title_identity(lineage_db):
    add_session(lineage_db, "original", "my project", 1)
    add_session(lineage_db, "unrelated", "MY PROJECT #2", 2)
    assert lineage_db.resolve_session_by_title("my project") == "original"
    assert lineage_db.get_next_title_in_lineage("my project") == "my project #2"
