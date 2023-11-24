from argparse import ArgumentParser

from .app import run


def main():
    parser = ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--redis-host", default="localhost")
    parser.add_argument("--port", type=int, default=5005)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
