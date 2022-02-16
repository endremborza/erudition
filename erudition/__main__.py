import sys

from .data_challenge.setup_dir import create_dir


def main(args):
    try:
        arg = args[1]
    except IndexError:
        arg = ""
    if arg == "challenge":
        try:
            target = args[3]
        except IndexError:
            target = "."
        create_dir(args[2], target)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv)
