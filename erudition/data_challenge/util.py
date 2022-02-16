from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from yaml import safe_load

from . import constants as const


@dataclass
class CConf:
    process: str
    setup: str = "sleep 0"
    etl: str = "sleep 0"
    image: str = "python:3.9"

    @classmethod
    def load(cls, solution):
        dic = safe_load((Path(solution) / const.CONF_PATH).read_text())
        return cls(**{k.split("-")[0]: v for k, v in dic.items() if v})


def get_obj(obj_name):
    return getattr(import_module(const.SPEC_MODULE), obj_name)
