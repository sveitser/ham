import os

from pathlib import Path

from ham.recency import encode_project_dir, format_age, last_session_mtime


def test_encode_project_dir_replaces_non_alnum():
    wt = Path("/home/u/.local/share/ham/home-u-r-org-repo/feat_x")
    assert encode_project_dir(wt) == "-home-u--local-share-ham-home-u-r-org-repo-feat-x"


def test_last_session_mtime_newest_jsonl(tmp_path):
    wt = Path("/r/org/repo/feat")
    session_dir = tmp_path / encode_project_dir(wt)
    session_dir.mkdir()
    old = session_dir / "a.jsonl"
    new = session_dir / "b.jsonl"
    other = session_dir / "notes.txt"
    for p in (old, new, other):
        p.write_text("x")
    os.utime(old, (100.0, 100.0))
    os.utime(new, (200.0, 200.0))
    os.utime(other, (300.0, 300.0))
    assert last_session_mtime(wt, projects_dir=tmp_path) == 200.0


def test_last_session_mtime_missing_dir(tmp_path):
    assert last_session_mtime(Path("/r/org/repo/feat"), projects_dir=tmp_path) is None


def test_last_session_mtime_no_jsonl(tmp_path):
    wt = Path("/r/org/repo/feat")
    session_dir = tmp_path / encode_project_dir(wt)
    session_dir.mkdir()
    (session_dir / "notes.txt").write_text("x")
    assert last_session_mtime(wt, projects_dir=tmp_path) is None


def test_format_age_none():
    assert format_age(None, 1000.0) == ""


def test_format_age_now():
    assert format_age(1000.0, 1030.0) == "now"


def test_format_age_minutes():
    assert format_age(1000.0, 1000.0 + 5 * 60) == "5m"


def test_format_age_hours():
    assert format_age(1000.0, 1000.0 + 3 * 3600) == "3h"


def test_format_age_days():
    assert format_age(1000.0, 1000.0 + 2 * 86400) == "2d"
