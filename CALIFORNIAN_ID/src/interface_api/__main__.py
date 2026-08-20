"""Enable `python -m interface_api [--host HOST] [--port PORT]`."""
from __future__ import annotations

import argparse

from .server import serve


def main() -> None:
    p = argparse.ArgumentParser(
        prog="interface_api",
        description="Tinkuy vertical-slice interface HTTP layer.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default=8791, type=int)
    p.add_argument("command", nargs="?", default="serve",
                   choices=["serve"])
    args = p.parse_args()
    if args.command == "serve":
        serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
