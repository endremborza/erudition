import io
from contextlib import redirect_stdout


def git_commit(c, addstr, msg):
    f = io.StringIO()
    with redirect_stdout(f):
        c.run("git config --get user.email")
    if not f.getvalue().strip():
        c.run('git config --local user.email "ci@cd.org"')
        c.run('git config --local user.name "CI/CD"')
    c.run(f'git add {addstr} && git commit -m "{msg}"')
