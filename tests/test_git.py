import pytest

from pathlib import Path

from ham.git import (
    classify_porcelain,
    discover_repos,
    repo_from_gitfile,
    resolve_repo,
)


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


def test_repo_from_gitfile():
    contents = "gitdir: /home/u/r/org/repo/.git/worktrees/feat\n"
    assert repo_from_gitfile(contents) == Path("/home/u/r/org/repo")


def test_repo_from_gitfile_no_gitdir():
    assert repo_from_gitfile("garbage\n") is None


def test_classify_porcelain_empty():
    assert classify_porcelain("") == (False, False)


def test_classify_porcelain_modified_only():
    assert classify_porcelain(" M src/foo.py") == (True, False)


def test_classify_porcelain_untracked_only():
    assert classify_porcelain("?? tmp/") == (False, True)


def test_classify_porcelain_both():
    assert classify_porcelain(" M src/foo.py\n?? tmp/\nA  new.py") == (True, True)


def test_classify_porcelain_empty_lines():
    assert classify_porcelain(" M src/foo.py\n\n?? tmp/") == (True, True)


def test_discover_repos_skips_files_in_org(tmp_path):
    (tmp_path / "org" / "repo" / ".git").mkdir(parents=True)
    (tmp_path / "org" / "file.txt").write_text("not a dir")
    result = discover_repos(tmp_path)
    assert result == [tmp_path / "org" / "repo"]


def test_discover_repos_skips_file_orgs(tmp_path):
    (tmp_path / "notanorg.txt").write_text("not a dir")
    (tmp_path / "org" / "repo" / ".git").mkdir(parents=True)
    result = discover_repos(tmp_path)
    assert result == [tmp_path / "org" / "repo"]
