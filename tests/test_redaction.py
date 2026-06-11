from __future__ import annotations

import unittest

from backbone_state_tracker.core.connectivity import sanitize_connection_error
from backbone_state_tracker.core.redaction import redact_payload, redact_sensitive_text


class RedactionTests(unittest.TestCase):
    def test_redacts_common_secret_patterns(self) -> None:
        text = (
            "password=Seoul!2026 token: abc123 "
            "Authorization: Bearer eyJhbGci "
            "snmp-server community private RO "
            "username admin secret 9 hashedValue"
        )

        redacted = redact_sensitive_text(text)

        self.assertNotIn("Seoul!2026", redacted)
        self.assertNotIn("abc123", redacted)
        self.assertNotIn("eyJhbGci", redacted)
        self.assertNotIn("private", redacted)
        self.assertNotIn("hashedValue", redacted)
        self.assertIn("***", redacted)

    def test_redacts_nested_payload_strings(self) -> None:
        payload = {
            "items": [
                {"output": "api_key: verySecret"},
                {"status": "GE1/0/1 UP"},
            ]
        }

        redacted = redact_payload(payload)

        self.assertEqual(redacted["items"][0]["output"], "api_key: ***")
        self.assertEqual(redacted["items"][1]["status"], "GE1/0/1 UP")

    def test_connection_errors_are_redacted_and_truncated(self) -> None:
        message = "password=SecretValue " + ("x" * 400)

        sanitized = sanitize_connection_error(message)

        self.assertNotIn("SecretValue", sanitized)
        self.assertLessEqual(len(sanitized), 300)


if __name__ == "__main__":
    unittest.main()
