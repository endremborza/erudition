import io
import json
from contextlib import redirect_stdout
from datetime import datetime
from distutils.dir_util import copy_tree
from functools import partial, reduce
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from uuid import uuid4
from zipfile import ZipFile

from invoke import UnexpectedExit, task
from structlog import get_logger

from ..util import git_commit
from . import constants as const
from .draw import dump_readme
from .util import CConf, get_obj

_RUNNER = "__r.sh"
_TIMER = "__t"

logger = get_logger(ctx="data challenge task")


class PackRepo:
    def __init__(self, pack_id) -> None:

        pack_loader = get_obj(const.PACK_FUNCTION)
        self.tmpfile = NamedTemporaryFile()
        pack_loader(pack_id, self.tmpfile.name)

    def dump_data(self, dirname):
        self._dump(dirname, [const.INPUT_FILENAME, const.RESULTS_FILENAME])

    def dump_inputs(self, dirname):
        self._dump(dirname, only=const.INPUT_FILENAME)

    def dump_results(self, dirname):
        self._dump(dirname, only=const.RESULTS_FILENAME)

    def cleanup(self):
        self.tmpfile.close()

    def _dump(self, dirname, exclude=(), only=None):
        with ZipFile(self.tmpfile.name) as zip_path:
            for cfp in zip_path.filelist:
                _name = cfp.filename
                if (_name in exclude) or (only and (_name != only)):
                    continue
                zip_path.extract(cfp, dirname)


@task
def test_solution(c, name, input_id, fail=True):
    pack_repo = PackRepo(input_id)
    _eval(c, name, pack_repo, input_id, fail, False, False)
    pack_repo.cleanup()


@task
def test_modified_solutions(
    c, input_id, fail=False, commit_logs=True, push_logs=True
):
    changed_solutions = _get_changes(c)
    if not changed_solutions:
        return
    pack_repo = PackRepo(input_id)
    for solution in changed_solutions:
        _eval(c, solution, pack_repo, input_id, fail, commit_logs, push_logs)
    pack_repo.cleanup()


@task
def get_test_pack(c):
    get_obj(const.PACK_FUNCTION)()


@task
def retag(c):
    if not _get_changes(c):
        return
    tag_name = f"{const.EVALED_GIT_TAG}-{uuid4().hex}"
    c.run(f"git tag {tag_name}")
    c.run(f"git push origin {tag_name}")
    c.run("git config --local pull.rebase true")
    c.run("git pull")
    dump_readme()
    git_commit(c, "README.md", "update readme")
    c.run("git pull; git push")


def _eval(
    c, solution_name, pack_repo: PackRepo, input_id, fail, commit_logs, push
):
    logger.info(f"evaluating solution {solution_name} on input {input_id}")
    sdir = Path.cwd() / solution_name
    contid = "challenge_dcont_eu"
    conf = CConf.load(solution_name)
    tmpdir = TemporaryDirectory()
    dirname = tmpdir.name
    eval_fun = get_obj(const.EVAL_FUNCTION)

    copy_tree(sdir, dirname)
    c.run(f"docker run -v {dirname}:/work --name {contid} -dt {conf.image}")
    _run = partial(_runcmd, c, contid)
    try:
        _run(conf.setup)
        pack_repo.dump_data(dirname)
        _run(conf.etl)
        pack_repo.dump_inputs(dirname)
        proc_time = _timed(conf.process, _run, dirname)
        pack_repo.dump_results(dirname)
        succ = eval_fun(
            dirname,
            json.loads((Path(dirname) / const.RESULTS_FILENAME).read_text()),
        )
        _run("rm -rf /work/*")
    except Exception as e:
        logger.exception(e)
        proc_time = float("inf")
        succ = False
    finally:
        c.run(f"docker kill {contid} && docker rm {contid}")
        tmpdir.cleanup()
        if fail:
            assert succ
        log_dic = {
            "name": solution_name,
            "input_id": input_id,
            "is_success": succ,
            "duration": proc_time,
            "commit": _gethash(c),
            "at": datetime.now().isoformat(),
        }

        _log(c, log_dic, commit_logs, push)


def _runcmd(c, containerid, comm):
    c.run(f"docker exec -w /work {containerid} {comm}")


def _timed(comm, runner, dirpath):
    timecomm = f"date +%s.%N >> {_TIMER}"
    sh_str = "\n".join(["#!/bin/sh", timecomm, comm, timecomm])
    Path(dirpath, _RUNNER).write_text(sh_str)
    runner(f"chmod +x {_RUNNER}")
    runner(f"./{_RUNNER}")
    start_time, end_time = map(
        float, Path(dirpath, _TIMER).read_text().strip().split("\n")
    )
    return end_time - start_time


def _gethash(c):
    f = io.StringIO()
    with redirect_stdout(f):
        c.run("git rev-parse --short HEAD")
    return f.getvalue().strip()


def _log(c, logdic, commit, push):
    logstr = json.dumps(logdic)
    logger.info("DONE", **logdic)
    lpath = Path(const.LOG_DIR)
    lpath.mkdir(exist_ok=True)
    log_id = uuid4().hex
    (lpath / f"{log_id}.json").write_text(logstr)
    if commit:
        git_commit(c, const.LOG_DIR, f"add logs {log_id[:8]}")
    else:
        return
    if not push:
        return
    c.run("git config --local pull.rebase true")
    for _ in range(6):
        try:
            c.run("git pull; git push")
            break
        except UnexpectedExit:
            pass


def _get_changes(c):
    tags = filter(
        lambda s: s.startswith(const.EVALED_GIT_TAG),
        _get_lines(c, "git tag"),
    )
    try:
        fun = partial(_get_diff_dirs, c)
        return [*reduce(set.intersection, map(fun, tags))]
    except TypeError:
        msg = f"no {const.EVALED_GIT_TAG} in {_get_lines(c, 'git tag')}"
        raise EnvironmentError(msg)


def _get_lines(c, comm):
    f = io.StringIO()
    with redirect_stdout(f):
        c.run(comm)
    return f.getvalue().strip().split("\n")


def _get_diff_dirs(c, base_commit):
    changes = set()
    for poss_ch in _get_lines(c, f"git diff {base_commit}..HEAD --name-only"):
        if (
            poss_ch.startswith(".")
            or poss_ch.startswith("__")
            or (not poss_ch)
        ):
            continue
        poss_dir = Path(poss_ch).parts[0]
        if Path(poss_dir).is_dir() and Path(poss_dir).exists():
            changes.add(poss_dir)
    return changes
