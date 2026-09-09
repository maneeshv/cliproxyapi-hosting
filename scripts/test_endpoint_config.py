"""Offline CLI configuration checks: python3 scripts/test_endpoint_config.py."""
import contextlib
import io
import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent


class EndpointConfigTests(unittest.TestCase):
    def test_invalid_configuration_never_loads_credentials_or_connects(self):
        invalid_urls = ["", "http://gateway.example.com", "https://", "https://@gateway.example.com",
                        "https://user:password@gateway.example.com", "https://gateway.example.com/v1",
                        "https://gateway.example.com//", "https://gateway.example.com?",
                        "https://gateway.example.com#", "https://gateway.example.com:bad",
                        "https://gateway.example.com:65536", "https://gateway.example.com:0",
                        "https://gate way.example.com", "https://gateway.example.com\n",
                        "https://gateway.example.com\\other", "https://[broken"]
        cases = [("check_public.py", []) , ("check_endpoint.py", [])]
        for url in invalid_urls:
            cases.extend([("check_public.py", [url]),
                          ("check_endpoint.py", ["--base-url", url, "--model", "example-model"])])
        cases.append(("check_endpoint.py", ["--base-url", "https://gateway.example.com"]))
        for script, args in cases:
            with self.subTest(script=script, args=args), patch.dict(os.environ, {}, clear=True), \
                    patch.object(sys, "argv", [script, *args]), contextlib.redirect_stderr(io.StringIO()), \
                    patch.object(Path, "read_text") as read_key, patch("getpass.getpass") as prompt, \
                    patch("http.client.HTTPSConnection") as connection, patch("urllib.request.build_opener") as opener:
                with self.assertRaises(SystemExit) as error:
                    runpy.run_path(str(SCRIPTS / script), run_name="__main__")
                self.assertEqual(error.exception.code, 2)
                for mock in (read_key, prompt, connection, opener):
                    mock.assert_not_called()

    def test_valid_origins_reach_key_loading(self):
        for origin in ("https://gateway.example.com", "https://gateway.example.com:8443/", "https://[::1]:443"):
            for script in ("check_public.py", "check_endpoint.py"):
                args = [origin] if script == "check_public.py" else ["--base-url", origin, "--model", "example-model", "--key-file", "unused"]
                with self.subTest(script=script, origin=origin), patch.dict(os.environ, {}, clear=True), \
                        patch.object(sys, "argv", [script, *args]), \
                        patch.object(Path, "read_text", side_effect=RuntimeError("key loading reached")):
                    with self.assertRaisesRegex(RuntimeError, "key loading reached"):
                        runpy.run_path(str(SCRIPTS / script), run_name="__main__")


if __name__ == "__main__":
    unittest.main()
