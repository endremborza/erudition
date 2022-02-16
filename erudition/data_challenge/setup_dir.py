import json
from distutils.dir_util import copy_tree
from pathlib import Path
from subprocess import call
from tempfile import TemporaryDirectory

from yaml import safe_load

from . import constants as const

root_repo = "https://github.com/endremborza/teaching"


def create_dir(challenge_name: str, target="."):
    tmp_dir = TemporaryDirectory()
    call(["git", "clone", root_repo, tmp_dir.name])
    ch_root = Path(tmp_dir.name) / "data-challenges"
    frame_dir = ch_root / "frame"
    ch_dir = ch_root / challenge_name
    out_dir = (Path(target) / f"{challenge_name}-challenge").as_posix()
    copy_tree(frame_dir.as_posix(), out_dir)
    copy_tree(ch_dir.as_posix(), out_dir)

    _conf = safe_load(Path(out_dir, const.CHALLENGE_YAML).read_text())
    priv_ids = _conf[const.PRIV_PACKID_KEY]
    pub_ids = _conf[const.PUB_PACKID_KEY]

    for _path, _pids in [
        (const.PR_GHA_PATH, pub_ids),
        (const.PUSH_GHA_PATH, pub_ids + priv_ids),
    ]:
        a_path = Path(out_dir, _path)
        a_str = a_path.read_text().replace("[...]", json.dumps(_pids))
        a_path.write_text(a_str)
    tmp_dir.cleanup()
