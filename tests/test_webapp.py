from __future__ import annotations

import unittest

from backbone_state_tracker.core.webapp import (
    DEFAULT_PORT,
    build_health_payload,
    build_home_page,
    run_smoke_check,
)
from backbone_state_tracker.core.version import APP_VERSION


class WebAppTests(unittest.TestCase):
    def test_home_page_is_korean_user_facing_webapp_screen(self) -> None:
        html = build_home_page()

        self.assertIn("백본 상태 추적기 웹앱", html)
        self.assertIn("샘플 검증 생성", html)
        self.assertIn("outputs", html)
        self.assertIn(APP_VERSION, html)

    def test_health_payload_marks_webapp_runtime(self) -> None:
        payload = build_health_payload()

        self.assertEqual(True, payload["ok"])
        self.assertEqual(APP_VERSION, payload["version"])
        self.assertEqual("webapp", payload["mode"])

    def test_webapp_smoke_check_passes_without_starting_server(self) -> None:
        self.assertEqual(0, run_smoke_check())

    def test_default_port_is_documented_runtime_port(self) -> None:
        self.assertEqual(8765, DEFAULT_PORT)


if __name__ == "__main__":
    unittest.main()
