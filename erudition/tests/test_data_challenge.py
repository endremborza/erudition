import os
import sys
from contextlib import contextmanager
from pathlib import Path

from invoke import Context

from erudition.data_challenge import constants, tasks
from erudition.data_challenge.setup_dir import create_dir
from erudition.util import git_commit


@contextmanager
def cd_into(dirpath):
    wd = os.getcwd()
    os.chdir(dirpath)
    sys.path.insert(0, str(dirpath))
    yield
    os.chdir(wd)
    sys.path.pop(0)


def test_full(tmp_path):
    ch_name = "test-challenge"
    create_dir(ch_name, target=tmp_path)

    with cd_into(tmp_path / f"{ch_name}-challenge"):
        c = Context()
        c.run("git init")
        git_commit(c, "* .github", "initial")
        _dummy_solution("s1", "{1: 2}")
        git_commit(c, "s1", "add s1")
        tasks.test_modified_solutions(c, "P-1", push_logs=False)
        _dummy_solution("s2", '{"X": 0}')
        git_commit(c, "s2", "add s2")
        tasks.test_modified_solutions(c, "P-1", push_logs=False)
        _dummy_solution("s2", '{"A": 10}')
        tasks.test_solution(c, "s2", "P-1")


def _dummy_solution(name, todump):
    Path(name).mkdir(exist_ok=True)
    Path(name, constants.CONF_PATH).write_text("process-command: python m.py")
    py_str = f"""open("output.json", "w").write('{todump}')"""
    Path(name, "m.py").write_text(py_str)
