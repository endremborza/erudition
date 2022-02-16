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
    pack_ids = safe_load(Path(out_dir, const.CHALLENGE_YAML).read_text())[
        const.PACKID_KEY
    ]
    action_path = Path(out_dir, const.ACTION_PATH)
    action_filled = action_path.read_text().replace(
        "[...]", json.dumps(pack_ids)
    )
    action_path.write_text(action_filled)

    tmp_dir.cleanup()
