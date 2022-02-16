import json
from pathlib import Path

import numpy as np
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
        .assign(mean=lambda df: df.mean(axis=1))
    )

    def _prettify(_df):
        sucs = _df.loc[:, "is_success"].pipe(lambda df: df > 0)
        return _df.loc[:, "duration"].style.apply(
            lambda s: np.where(
                sucs.loc[:, s.name],
                "background-color:##90ee90",
                "background-color:#ffcccb",
            )
        )

    bot_html = fresh_things.loc[~succ_ser, :].pipe(_prettify).to_html()
    top_html = good_ones.sort_values("mean").to_html()
    if True:  # until styling doesn't work... TODO
        bot_html = fresh_things.loc[~succ_ser, "duration"].to_html()

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
