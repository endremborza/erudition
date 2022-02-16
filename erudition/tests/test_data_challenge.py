from pathlib import Path

import pytest
from invoke import Context

from erudition.__main__ import main
from erudition.data_challenge import constants, tasks
from erudition.util import cd_into, git_commit


def test_full(tmp_path):
    c = Context()
    origin_path = tmp_path / "origin"
    origin_path.mkdir(exist_ok=True)
    with cd_into(origin_path):
        c.run("git init -b main")
        c.run("git checkout -b tmp")

    ch_name = "test-challenge"
    main([None, "challenge", ch_name, tmp_path])

    with cd_into(tmp_path / f"{ch_name}-challenge"):
        c.run(f"git remote add origin {origin_path}")
        c.run("git push -u origin main")
        with cd_into(origin_path):
            c.run("git checkout main")
            with pytest.raises(EnvironmentError):
                tasks.test_modified_solutions(c, "P-1")
            c.run("git checkout -b tmp")
        c.run("git push --tags origin")
        _dummy_solution("s1", "{1: 2}")
        git_commit(c, "s1", "add s1")
        tasks.test_modified_solutions(c, "P-1")
        tasks.retag(c)
        _dummy_solution("s2", '{"X": 0}')
        git_commit(c, "s2", "add s2")
        tasks.test_modified_solutions(c, "P-1")
        tasks.retag(c)
        tasks.test_modified_solutions(c, "P-1")
        _dummy_solution("s2", '{"A": 10}')
        tasks.test_solution(c, "s2", "P-1")
        tasks.get_test_pack(c)


def _dummy_solution(name, todump):
    Path(name).mkdir(exist_ok=True)
    Path(name, constants.CONF_PATH).write_text("process-command: python m.py")
    py_str = f"""open("output.json", "w").write('{todump}')"""
    Path(name, "m.py").write_text(py_str)
