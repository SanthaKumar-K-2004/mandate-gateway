"""
Mandate Gateway — Environment Parser Unit Tests
Section S00.3 — Security & Configuration Hardening
"""

import os
import tempfile
import unittest

from apps.api.config.env_loader import load_env_file


class TestEnvLoader(unittest.TestCase):
    """Focused unit tests for hardened .env parser."""

    def test_load_env_file_comprehensive(self) -> None:
        content = (
            "# This is a header comment\n"
            "   \n"  # blank line with whitespace
            "SIMPLE_KEY=simple_val\n"
            'DOUBLE_QUOTED="hello world"\n'
            "SINGLE_QUOTED='hello universe'\n"
            "WITH_INLINE_COMMENT=foo # this is an inline comment\n"
            'QUOTED_WITH_HASH="foo#bar"\n'
            "EMPTY_VAL=\n"
            "DUPLICATE_KEY=first_val\n"
            "DUPLICATE_KEY=second_val\n"
            "EQUALS_IN_VAL=key=value=with=equals\n"
            "export BASH_EXPORT_KEY=export_val\n"
            "UNICODE_KEY=🚀_mandate_gateway_🔐\n"
            "CRLF_KEY=crlf_value\r\n"
            "MALFORMED_LINE_WITHOUT_EQUALS\n"
        )

        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
            f.write(content)
            temp_path = f.name

        try:
            res = load_env_file(temp_path)
            self.assertEqual(res["SIMPLE_KEY"], "simple_val")
            self.assertEqual(res["DOUBLE_QUOTED"], "hello world")
            self.assertEqual(res["SINGLE_QUOTED"], "hello universe")
            self.assertEqual(res["WITH_INLINE_COMMENT"], "foo")
            self.assertEqual(res["QUOTED_WITH_HASH"], "foo#bar")
            self.assertEqual(res["EMPTY_VAL"], "")
            self.assertEqual(res["DUPLICATE_KEY"], "second_val")  # later overrides earlier
            self.assertEqual(res["EQUALS_IN_VAL"], "key=value=with=equals")
            self.assertEqual(res["BASH_EXPORT_KEY"], "export_val")
            self.assertEqual(res["UNICODE_KEY"], "🚀_mandate_gateway_🔐")
            self.assertEqual(res["CRLF_KEY"], "crlf_value")
            self.assertNotIn("MALFORMED_LINE_WITHOUT_EQUALS", res)
        finally:
            if os.path.isfile(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
