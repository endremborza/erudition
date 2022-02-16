CHALLENGE_YAML = "challenge.yaml"
PRIV_PACKID_KEY = "private-ids"
PUB_PACKID_KEY = "public-ids"
LOG_DIR = ".logs"

CONF_PATH = "conf.yaml"
SETUP_COMM = "setup-command"
ETL_COMM = "etl-command"
PROC_COMM = "process-command"


RESULTS_FILENAME = "results.json"
INPUT_FILENAME = "input.json"

SPEC_MODULE = "chspec"
PACK_FUNCTION = "load_pack"
EVAL_FUNCTION = "evaluate"


PR_GHA_PATH, PUSH_GHA_PATH = [
    f".github/workflows/run-{k}.yml" for k in ["pr", "full"]
]

EVALED_GIT_TAG = "eval-checkpoint"
