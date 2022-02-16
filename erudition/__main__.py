import sys

from .data_challenge.setup_dir import create_dir

if __name__ == "__main__":
    try:
        arg = sys.argv[1]
    except IndexError:
        arg = ""
    if arg == "challenge":
        create_dir(sys.argv[2])
