from invoke import Collection

from . import tasks

data_ns = Collection.from_module(tasks)
