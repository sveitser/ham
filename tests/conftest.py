import pytest

from ham import cli, git
from ham.config import Config


@pytest.fixture(autouse=True)
def _redirect_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(git, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cli, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cli, "load_config", lambda: Config.defaults())
