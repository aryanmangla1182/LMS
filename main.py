"""Entrypoint for the LMS backend engine."""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_PATH = os.path.join(CURRENT_DIR, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from lms_engine.bootstrap import build_container
from lms_engine.api.http import create_server


def main() -> None:
    container = build_container()
    server = create_server(container)
    print("LMS engine listening on http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
