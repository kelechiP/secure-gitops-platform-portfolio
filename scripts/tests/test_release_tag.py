import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock

SPEC = importlib.util.spec_from_file_location(
    "check_release_tag", Path(__file__).resolve().parents[1] / "check_release_tag.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class ReleaseTagTests(unittest.TestCase):
    def check(self, responses):
        request = Mock(side_effect=responses)
        guard.require_unused_tag("ghcr.io/example/service", "v1.2.3", "actor", "test-only", request)
        return request

    def prefix(self):
        return [(200, {"token": "test-only"}),
                (200, {"name": "example/service", "tags": ["v2.0.0"]})]

    def test_new_version_is_allowed_and_only_version_is_checked(self):
        request = self.check(self.prefix() + [
            (404, {"errors": [{"code": "MANIFEST_UNKNOWN"}]})])
        self.assertEqual(request.call_count, 3)
        self.assertEqual(request.call_args.args[0],
                         "https://ghcr.io/v2/example/service/manifests/v1.2.3")

    def test_existing_version_is_refused(self):
        with self.assertRaises(guard.ReleaseBlocked):
            self.check(self.prefix() + [(200, {"schemaVersion": 2})])

    def test_ambiguous_responses_are_refused(self):
        for status, body in [(401, {}), (403, {}), (429, {}), (500, {}),
                             (404, {}), (404, {"errors": []}),
                             (404, {"errors": [{"code": "NAME_UNKNOWN"}]}),
                             (404, {"errors": [{"code": "MANIFEST_UNKNOWN"}, {"code": "DENIED"}]}),
                             (302, {}), (404, "<html>")]:
            with self.subTest(status=status, body=body), self.assertRaises(guard.ReleaseBlocked):
                self.check(self.prefix() + [(status, body)])

    def test_authentication_and_package_access_fail_closed(self):
        for responses in [[(401, {})], [(200, {})], [(200, {"token": ""})],
                          [self.prefix()[0], (404, {})],
                          [self.prefix()[0], (200, {"name": "wrong", "tags": []})]]:
            with self.subTest(responses=responses), self.assertRaises(guard.ReleaseBlocked):
                self.check(responses)

    def test_network_failure_cannot_allow_publication(self):
        with self.assertRaises(TimeoutError):
            self.check(self.prefix() + [TimeoutError()])

    def test_invalid_inputs_do_not_send_credentials(self):
        request = Mock()
        for image, version, actor, token in [
            ("https://other.example/image", "v1.2.3", "actor", "test"),
            ("ghcr.io/example/service", "latest", "actor", "test"),
            ("ghcr.io/example/service", "v01.2.3", "actor", "test"),
            ("ghcr.io/example/service", "v1.2.3", "actor", "")]:
            with self.subTest(image=image, version=version), self.assertRaises(guard.ReleaseBlocked):
                guard.require_unused_tag(image, version, actor, token, request)
        request.assert_not_called()

    def test_credentials_are_not_forwarded_on_redirect(self):
        self.assertIsNone(guard.NoRedirects().redirect_request(
            None, None, 302, "", {}, "https://other.example"))


if __name__ == "__main__":
    unittest.main()
