import json
from pathlib import Path

import pandas as pd

from . import constants as const


def dump_readme():
    lpath = Path(const.LOG_DIR)
    df = pd.DataFrame(
        map(json.loads, map(Path.read_text, lpath.glob("*.json")))
    )
    fresh_things = (
        df.sort_values("at")
        .groupby(["commit", "name", "input_id"])
        .last()
        .reset_index()
        .pivot_table(index=["name", "commit"], columns="input_id")
    )
    succ_ser = fresh_things["is_success"].fillna(0).all(axis=1)
    good_ones = (
        fresh_things.loc[succ_ser, "duration"]
        .loc[:, lambda df: df.mean().sort_values().index]
        .assign(**{"Total time": lambda df: df.sum(axis=1)})
        .sort_values("Total time")
        .round(4)
    )

    top_html = good_ones.to_html()
    bot_html = fresh_things.loc[~succ_ser, :].to_html()

    out_str = "\n\n".join(
        [
            "# Results",
            "## Successful Solutions",
            top_html,
            "## Near Misses",
            bot_html,
        ]
    )
    Path("README.md").write_text(out_str)
