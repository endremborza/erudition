import io
import json
from contextlib import redirect_stdout
from distutils.dir_util import copy_tree
from functools import partial
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from uuid import uuid4
from zipfile import ZipFile

from invoke import UnexpectedExit, task
from structlog import get_logger

from . import constants as const
from .util import CConf, get_obj

_RUNNER = "__r.sh"
_TIMER = "__t"
_LOGDIR = Path(".logs")

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
def test_solution(c, name, input_id):
    pack_repo = PackRepo(input_id)
    _eval(c, name, pack_repo, input_id)
    pack_repo.cleanup()
    _retag(c)


@task
def test_modified_solutions(c, input_id):
    changed_solutions = _get_changes(c)
    if not changed_solutions:
        return
    pack_repo = PackRepo(input_id)
    for solution in changed_solutions:
        _eval(c, solution, pack_repo, input_id)
    pack_repo.cleanup()
    _retag(c)


@task
def get_test_pack(c):
    get_obj(const.PACK_FUNCTION)()


def _eval(c, solution_name, pack_repo: PackRepo, input_id):
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
    except Exception as e:
        logger.exception(e)
        proc_time = float("inf")
        succ = False
    finally:
        _log(c, solution_name, input_id, succ, proc_time, _gethash(c))
        c.run(f"docker kill {contid} && docker rm {contid}")
        tmpdir.cleanup()


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
    try:
        with redirect_stdout(f):
            c.run("git rev-parse --short HEAD")
        return f.getvalue()
    except UnexpectedExit:
        return


def _log(c, solution_name, input_id, result, proc_time, commit_hash):
    logdic = {
        "name": solution_name,
        "input_id": input_id,
        "is_success": result,
        "duration": proc_time,
        "commit": commit_hash,
    }
    logstr = json.dumps(logdic)
    logger.info("DONE", **logdic)
    _LOGDIR.mkdir(exist_ok=True)
    log_id = uuid4().hex
    (_LOGDIR / f"{log_id}.json").write_text(logstr)
    c.run(f'git add {_LOGDIR} && git commit -m "add logs {log_id[:8]}"')
    c.run("git pull; git push")


def _get_changes(c):
    tags = io.StringIO()
    base_commit = const.EVALED_GIT_TAG
    with redirect_stdout(tags):
        c.run("git tag")

    if base_commit not in tags.getvalue():
        comm_zero = io.StringIO()
        with redirect_stdout(comm_zero):
            c.run("git rev-list --max-parents=0 HEAD")
        base_commit = comm_zero.getvalue().strip().split("\n")[0]

    f = io.StringIO()
    with redirect_stdout(f):
        c.run(f"git diff {base_commit}..HEAD --name-only")

    changes = set()
    for poss_ch in f.getvalue().strip().split("\n"):
        if poss_ch.startswith("."):
            continue
        poss_dir = Path(poss_ch).parts[0]
        if Path(poss_dir).is_dir and Path(poss_dir).exists():
            changes.add(poss_dir)
    return [*changes]


def _retag(c):
    c.run(f"git tag -f {const.EVALED_GIT_TAG}")

    # tag all of the differently and only eval the ones that diff from all tags