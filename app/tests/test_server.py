import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import server  # noqa: E402


class ServerTests(unittest.TestCase):
    def test_service_info_has_expected_identity(self):
        info = server.service_info()
        self.assertEqual(info["service"], "secure-gitops-platform-portfolio")
        self.assertIn("version", info)
        self.assertIn("environment", info)

    def test_metrics_are_prometheus_compatible(self):
        output = server.metrics()
        self.assertIn("platform_http_requests_total", output)
        self.assertIn("platform_uptime_seconds", output)
        self.assertTrue(output.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
