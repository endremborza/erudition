import json
from pathlib import Path

import pandas as pd

from . import constants as const


def dump_readme():
    lpath = Path(const.LOG_DIR)
    df = (
        pd.DataFrame(
            map(json.loads, map(Path.read_text, lpath.glob("*.json")))
        )
        .sort_values("at")
        .pipe(
            lambda _df: _df.merge(
                _df.groupby(["name", "commit"])["at"]
                .first()
                .sort_values()
                .reset_index()
                .groupby("name")
                .apply(
                    lambda gdf: gdf.assign(
                        v=[
                            f"[v{i + 1}](../../commit/{gdf['commit'].iloc[i]})"
                            for i in range(gdf.shape[0])
                        ]
                    )
                )[["v", "commit"]]
                .reset_index()
            )
        )
    )
    fresh_things = (
        df.groupby(["v", "name", "input_id"])
        .last()
        .reset_index()
        .pivot_table(index=["name", "v"], columns="input_id")
    )
    succ_ser = fresh_things["is_success"].fillna(0).all(axis=1)
    good_ones = (
        fresh_things.loc[succ_ser, "duration"]
        .loc[:, lambda df: df.mean().sort_values().index]
        .assign(**{"Total time": lambda df: df.sum(axis=1)})
        .sort_values("Total time")
        .round(4)
        .reset_index()
    )

    top_render = good_ones.to_markdown(index=False)
    bot_html = (
        fresh_things.loc[~succ_ser, "duration"]
        .reset_index()
        .to_markdown(index=False)
    )

    out_str = "\n\n".join(
        [
            "# Results",
            "## Successful Solutions",
            top_render,
            "## Near Misses",
            bot_html,
        ]
    )
    Path("README.md").write_text(out_str)
