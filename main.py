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
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    if len(sys.argv) >= 3 and sys.argv[1] == "runserver":
        port = int(sys.argv[2])
    server = create_server(container, host=host, port=port)
    print("LMS engine listening on http://{0}:{1}".format(host, port))
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
