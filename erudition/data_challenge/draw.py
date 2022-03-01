import json
from pathlib import Path
from subprocess import check_output

import numpy as np
import pandas as pd
from checksumdir import dirhash

from . import constants as const


def checkout(target):
    check_output(["git", "checkout", target])


def _add_link_col(gdf):
    return gdf.assign(
        v=[
            f"[v{i + 1}](../../commit/{gdf['true_commit'].iloc[i]})"
            for i in range(gdf.shape[0])
        ]
    )


def dump_readme():
    lpath = Path(const.LOG_DIR)
    base_df = pd.DataFrame(
        map(json.loads, map(Path.read_text, lpath.glob("*.json")))
    )

    hash_recs = []
    for _rec in (
        base_df[["name", "commit", "at"]]
        .drop_duplicates(subset=["name", "commit"])
        .to_dict("records")
    ):
        checkout(_rec["commit"])
        _md = dirhash(_rec["name"], "md5")
        hash_recs.append({"dirhash": _md, **_rec})
    checkout("main")

    true_c_df = pd.DataFrame(hash_recs).pipe(
        lambda df: df.merge(
            df.sort_values("at")
            .groupby(["name", "dirhash"])["commit"]
            .first()
            .rename("true_commit")
            .reset_index()
        ).drop("at", axis=1)
    )

    fresh_things = (
        base_df.merge(true_c_df)
        .sort_values("at")
        .pipe(
            lambda _df: _df.merge(
                _df.groupby(["name", "true_commit"])["at"]
                .first()
                .sort_values()
                .reset_index()
                .groupby("name")
                .apply(_add_link_col)[["v", "true_commit", "name"]]
            )
        )
        .groupby(["v", "name", "input_id"])
        .last()
        .reset_index()
        .pivot_table(index=["name", "v"], columns="input_id")
    )
    succ_ser = fresh_things["is_success"].fillna(0).all(axis=1)
    top_render = (
        fresh_things.loc[succ_ser, "duration"]
        .loc[:, lambda df: df.mean().sort_values().index]
        .assign(**{"Total time": lambda df: df.sum(axis=1)})
        .sort_values("Total time")
        .round(4)
        .reset_index()
        .to_markdown(index=False)
    )

    bot_render = (
        fresh_things.loc[~succ_ser, :]
        .pipe(
            lambda df: df.loc[:, "duration"].apply(
                lambda s: np.where(
                    df.loc[:, ("is_success", s.name)], s, np.nan
                )
            )
        )
        .reset_index()
        .to_markdown(index=False)
    )

    out_str = "\n\n".join(
        [
            "# Results",
            "## Successful Solutions",
            top_render,
            "## Near Misses",
            bot_render,
        ]
    )
    Path("README.md").write_text(out_str)
