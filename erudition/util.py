import os
import sys
from contextlib import contextmanager

from invoke import UnexpectedExit


def git_commit(c, addstr, msg):
    try:
        c.run("git config --get user.email")
        c.run("git config --get user.name")
    except UnexpectedExit:
        c.run('git config --local user.email "ci@cd.org"')
        c.run('git config --local user.name "CI/CD"')
    c.run(f'git add {addstr} && git commit -m "{msg}"')


@contextmanager
def cd_into(dirpath):
    wd = os.getcwd()
    os.chdir(dirpath)
    sys.path.insert(0, str(dirpath))
    yield
    os.chdir(wd)
    sys.path.pop(0)
