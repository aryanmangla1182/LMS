import os
import sys
import unittest
from io import StringIO
from unittest.mock import patch


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import main


class FakeServer:
    def __init__(self) -> None:
        self.serve_forever_called = False
        self.server_close_called = False

    def serve_forever(self) -> None:
        self.serve_forever_called = True

    def server_close(self) -> None:
        self.server_close_called = True


class MainEntryPointTestCase(unittest.TestCase):
    def test_runserver_uses_requested_port(self) -> None:
        fake_server = FakeServer()

        with patch.object(main, "build_container", return_value="container") as mock_build_container:
            with patch.object(main, "create_server", return_value=fake_server) as mock_create_server:
                with patch.object(sys, "argv", ["main.py", "runserver", "8001"]):
                    stdout = StringIO()
                    with patch("sys.stdout", stdout):
                        main.main()

        mock_build_container.assert_called_once_with()
        mock_create_server.assert_called_once_with("container", host="127.0.0.1", port=8001)
        self.assertTrue(fake_server.serve_forever_called)
        self.assertTrue(fake_server.server_close_called)
        self.assertIn("http://127.0.0.1:8001", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
