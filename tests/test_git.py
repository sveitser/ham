import pytest

from ham.git import discover_repos, resolve_repo


def test_discover_repos(tmp_path):
    (tmp_path / "org1" / "repo1" / ".git").mkdir(parents=True)
    (tmp_path / "org2" / "repo2" / ".git").mkdir(parents=True)
    result = discover_repos(tmp_path)
    assert result == [tmp_path / "org1" / "repo1", tmp_path / "org2" / "repo2"]


def test_discover_repos_skips_non_git(tmp_path):
    (tmp_path / "org" / "notrepo").mkdir(parents=True)
    result = discover_repos(tmp_path)
    assert result == []


def test_discover_repos_empty(tmp_path):
    assert discover_repos(tmp_path) == []


def test_discover_repos_missing_dir(tmp_path):
    assert discover_repos(tmp_path / "nonexistent") == []


def test_resolve_repo_unique(tmp_path):
    (tmp_path / "org1" / "myrepo" / ".git").mkdir(parents=True)
    assert resolve_repo("myrepo", tmp_path) == tmp_path / "org1" / "myrepo"


def test_resolve_repo_no_match(tmp_path):
    (tmp_path / "org1" / "repo1" / ".git").mkdir(parents=True)
    with pytest.raises(ValueError, match="no repo found"):
        resolve_repo("missing", tmp_path)


def test_resolve_repo_multiple(tmp_path):
    (tmp_path / "org1" / "samename" / ".git").mkdir(parents=True)
    (tmp_path / "org2" / "samename" / ".git").mkdir(parents=True)
    with pytest.raises(ValueError, match="multiple repos found"):
        resolve_repo("samename", tmp_path)
