"""``dsl`` reads the ``.env`` in the folder it is run from.

Called from this file, not through ``python -c``: python-dotenv searches
from the *calling file's* folder unless told to use the current one, and
``python -c`` hides that because dotenv treats it as interactive. An
installed ``dsl`` is a file in site-packages, so a student's ``.env``
would never be found.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("dotenv")


def test_the_env_file_in_the_current_folder_is_read(tmp_path, monkeypatch):
    from dissyslab.cli import _load_env

    (tmp_path / ".env").write_text("DSL_TEST_ENV_PROBE=from-the-office-folder\n",
                                   encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DSL_TEST_ENV_PROBE", raising=False)
    _load_env()
    try:
        assert os.environ.get("DSL_TEST_ENV_PROBE") == "from-the-office-folder"
    finally:
        os.environ.pop("DSL_TEST_ENV_PROBE", None)
