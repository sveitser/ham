import pytest

from ham import cli, git


@pytest.fixture(autouse=True)
def _redirect_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(git, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cli, "DATA_DIR", tmp_path)
