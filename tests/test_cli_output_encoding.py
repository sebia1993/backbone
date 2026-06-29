from __future__ import annotations

import unittest

from backbone_state_tracker import app


class ReconfigurableStream:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def reconfigure(self, **kwargs: str) -> None:
        self.calls.append(kwargs)


class FailingStream:
    def reconfigure(self, **kwargs: str) -> None:
        raise OSError("stream is closed")


class CliOutputEncodingTests(unittest.TestCase):
    def test_configures_streams_as_utf8(self) -> None:
        stdout = ReconfigurableStream()
        stderr = ReconfigurableStream()

        app._configure_cli_output_encoding(stdout, stderr)

        expected = {"encoding": "utf-8", "errors": "backslashreplace"}
        self.assertEqual([expected], stdout.calls)
        self.assertEqual([expected], stderr.calls)

    def test_ignores_streams_that_cannot_be_reconfigured(self) -> None:
        app._configure_cli_output_encoding(None, object(), FailingStream())


if __name__ == "__main__":
    unittest.main()
