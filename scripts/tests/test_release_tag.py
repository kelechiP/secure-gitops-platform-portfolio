import base64
import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

SPEC = importlib.util.spec_from_file_location(
    "check_release_tag", Path(__file__).resolve().parents[1] / "check_release_tag.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

IMAGE = "ghcr.io/example/service"
VERSION = "v1.2.3"
SECRET = "test-credential-sentinel"
TOKEN = "test-registry-token-sentinel"
AUTH = (200, {"token": TOKEN})
PACKAGE = (200, {"name": "example/service", "tags": ["v2.0.0"]})


def missing(code):
    return 404, {"errors": [{"code": code, "message": "not found"}]}


class ReleaseTagTests(unittest.TestCase):
    def check(self, responses):
        request = Mock(side_effect=responses)
        result = guard.require_unused_tag(IMAGE, VERSION, "actor", SECRET, request)
        return result, request

    def test_first_package_requires_token_then_canonical_name_unknown(self):
        result, request = self.check([AUTH, missing("NAME_UNKNOWN")])
        self.assertEqual(result, "package_absent")
        self.assertEqual(request.call_count, 2)
        self.assertIn("service=ghcr.io&scope=repository%3Aexample%2Fservice%3Apull",
                      request.call_args_list[0].args[0])
        self.assertEqual(request.call_args_list[0].args[1],
                         "Basic " + base64.b64encode(f"actor:{SECRET}".encode()).decode())
        self.assertEqual(request.call_args.args[0], "https://ghcr.io/v2/example/service/tags/list?n=1")
        self.assertEqual(request.call_args.args[1], f"Bearer {TOKEN}")

    def test_existing_package_unused_exact_version(self):
        for tags in ([], ["v2.0.0"]):
            with self.subTest(tags=tags):
                result, request = self.check([
                    AUTH, (200, {"name": "example/service", "tags": tags}), missing("MANIFEST_UNKNOWN")])
                self.assertEqual(result, "version_absent")
                self.assertEqual(request.call_count, 3)
                self.assertEqual(request.call_args.args[0],
                                 "https://ghcr.io/v2/example/service/manifests/v1.2.3")

    def test_existing_version_blocks_even_with_unreadable_manifest(self):
        for payload in ({"schemaVersion": 2}, {}, None):
            with self.subTest(payload=payload), self.assertRaises(guard.ReleaseBlocked) as caught:
                self.check([AUTH, PACKAGE, (200, payload)])
            self.assertEqual(caught.exception.reason, "exists")
        with self.assertRaises(guard.ReleaseBlocked) as caught:
            self.check([AUTH, (200, {"name": "example/service", "tags": [VERSION]})])
        self.assertEqual(caught.exception.reason, "exists")

    def test_unexpected_status_at_every_stage_blocks(self):
        for prefix in ([], [AUTH], [AUTH, PACKAGE]):
            for status in (201, 202, 204, 206, 301, 302, 303, 307, 308, 400, 401, 403, 405, 429, 500, 503):
                with self.subTest(stage=len(prefix), status=status), self.assertRaises(guard.ReleaseBlocked):
                    self.check(prefix + [(status, missing("NAME_UNKNOWN")[1])])

    def test_authentication_and_authorization_are_distinct(self):
        for prefix in ([], [AUTH], [AUTH, PACKAGE]):
            for status in (401, 403):
                with self.subTest(stage=len(prefix), status=status), self.assertRaises(guard.ReleaseBlocked) as caught:
                    self.check(prefix + [(status, {})])
                self.assertEqual(caught.exception.reason, "auth")
        for payload in ({}, None, [], "", {"token": ""}, {"token": " "}, {"token": 1},
                        {"token": "bad\r\nheader"}, {"token": TOKEN, "errors": []}):
            with self.subTest(payload=payload), self.assertRaises(guard.ReleaseBlocked):
                self.check([(200, payload)])
        with self.assertRaises(guard.ReleaseBlocked):
            self.check([missing("NAME_UNKNOWN")])

    def test_only_expected_error_code_and_shape_can_allow_absence(self):
        for prefix, accepted, wrong in (([AUTH], "NAME_UNKNOWN", "MANIFEST_UNKNOWN"),
                                         ([AUTH, PACKAGE], "MANIFEST_UNKNOWN", "NAME_UNKNOWN")):
            payloads = [None, "<html>", [], {}, {"errors": []}, {"errors": {}},
                        {"errors": [None]}, {"errors": [{"code": wrong}]},
                        {"errors": [{"code": accepted.lower()}]},
                        {"errors": [{"code": accepted + " "}]},
                        {"errors": [{"code": accepted}, {"code": "DENIED"}]},
                        {"errors": [{"code": accepted, "message": []}]},
                        {"errors": [{"code": accepted}], "token": TOKEN},
                        {"errors": [{"code": accepted, "unexpected": True}]}]
            for payload in payloads:
                with self.subTest(stage=len(prefix), payload=payload), self.assertRaises(guard.ReleaseBlocked):
                    self.check(prefix + [(404, payload)])

    def test_tag_list_must_establish_repository_access(self):
        for payload in ({}, None, [], {"name": "wrong", "tags": []},
                        {"name": "example/service", "tags": None},
                        {"name": "example/service", "tags": [1]},
                        {"name": "example/service", "tags": ["invalid/tag"]},
                        {"name": "example/service", "tags": [], "errors": []}):
            with self.subTest(payload=payload), self.assertRaises(guard.ReleaseBlocked):
                self.check([AUTH, (200, payload)])

    def test_network_failures_sanitize_exception_and_cli_output(self):
        for prefix in ([], [AUTH], [AUTH, PACKAGE]):
            for error in (TimeoutError(SECRET), URLError(f"Authorization: Bearer {TOKEN}"), OSError(SECRET)):
                with self.subTest(stage=len(prefix), error=type(error).__name__):
                    with self.assertRaises(guard.ReleaseBlocked) as caught:
                        self.check(prefix + [error])
                    self.assertNotIn(SECRET, str(caught.exception))
                    self.assertNotIn(TOKEN, str(caught.exception))
                    stdout, stderr = io.StringIO(), io.StringIO()
                    with patch.object(guard, "require_unused_tag", side_effect=caught.exception), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        self.assertEqual(guard.main(), 1)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertNotIn(SECRET, stderr.getvalue())
                    self.assertNotIn(TOKEN, stderr.getvalue())
                    self.assertNotIn("Authorization", stderr.getvalue())

    def test_cli_distinguishes_both_successes_and_existing_version(self):
        for result in ("package_absent", "version_absent"):
            out = io.StringIO()
            with patch.object(guard, "require_unused_tag", return_value=result), contextlib.redirect_stdout(out):
                self.assertEqual(guard.main(), 0)
            self.assertEqual(out.getvalue().strip(), guard.RESULTS[result])
        err = io.StringIO()
        with patch.object(guard, "require_unused_tag", side_effect=guard.ReleaseBlocked("exists")), contextlib.redirect_stderr(err):
            self.assertEqual(guard.main(), 1)
        self.assertIn("already exists", err.getvalue())
        self.assertNotEqual(guard.RESULTS["package_absent"], guard.RESULTS["version_absent"])

    def test_invalid_inputs_send_no_credentials(self):
        request = Mock()
        cases = [(image, VERSION) for image in (
            "http://ghcr.io/example/service", "ghcr.io.evil/example/service", "GHCR.IO/example/service",
            "ghcr.io/example/../service", "ghcr.io/example//service", "ghcr.io/example/service?query",
            "other.example/service", "ghcr.io/example/service#fragment", "ghcr.io:443/example/service")]
        cases += [(IMAGE, version) for version in ("latest", "v01.2.3", "v1.2.3-rc1", "v1.2", "v1.2.3\n")]
        for image, version in cases:
            with self.subTest(image=image, version=version), self.assertRaises(guard.ReleaseBlocked):
                guard.require_unused_tag(image, version, "actor", SECRET, request)
        for actor, credential in (("", SECRET), ("actor", ""), ("actor:other", SECRET)):
            with self.assertRaises(guard.ReleaseBlocked):
                guard.require_unused_tag(IMAGE, VERSION, actor, credential, request)
        request.assert_not_called()


class RegistryTransportTests(unittest.TestCase):
    url = "https://ghcr.io/v2/example/service/tags/list?n=1"

    def response(self, body, status=200, url=None):
        response = io.BytesIO(body)
        response.code = status
        response.geturl = lambda: url or self.url
        return response

    def test_timeout_bound_body_and_authorization_header(self):
        with patch.object(guard, "build_opener") as build:
            build.return_value.open.return_value = self.response(b'{"tags": []}')
            self.assertEqual(guard.request_json(self.url, f"Bearer {TOKEN}"), (200, {"tags": []}))
            args, kwargs = build.return_value.open.call_args
            self.assertEqual(kwargs, {"timeout": 30})
            self.assertEqual(args[0].get_header("Authorization"), f"Bearer {TOKEN}")
            self.assertIsInstance(build.call_args.args[0], guard.NoRedirects)

    def test_http_error_body_is_parsed_but_never_logged(self):
        body = json.dumps(missing("NAME_UNKNOWN")[1]).encode()
        error = HTTPError(self.url, 404, "Not found", {}, io.BytesIO(body))
        with patch.object(guard, "build_opener") as build:
            build.return_value.open.side_effect = error
            self.assertEqual(guard.request_json(self.url, f"Bearer {TOKEN}"), missing("NAME_UNKNOWN"))

    def test_empty_malformed_duplicate_nonstandard_and_oversized_json_block(self):
        for body in (b'', b'<html>', b'{', b'\xff', b'{"token":"a","token":"b"}',
                     b'{"value": NaN}', b' ' * (guard.MAX_RESPONSE_BYTES + 1)):
            with self.subTest(length=len(body)), patch.object(guard, "build_opener") as build:
                build.return_value.open.return_value = self.response(body)
                with self.assertRaises(guard.ReleaseBlocked):
                    guard.request_json(self.url, f"Bearer {TOKEN}")

    def test_redirect_handler_does_not_follow_same_or_other_host(self):
        handler = guard.NoRedirects()
        handler.parent = Mock()
        for code in (301, 302, 303, 307, 308):
            for destination in ("https://ghcr.io/elsewhere", "https://other.example/"):
                with self.subTest(code=code, destination=destination):
                    self.assertIsNone(handler.http_error_302(
                        Request(self.url), io.BytesIO(), code, "redirect", {"location": destination}))
        handler.parent.open.assert_not_called()

    def test_redirect_status_or_changed_effective_url_blocks(self):
        for status, url in ((302, self.url), (200, "https://other.example/")):
            with patch.object(guard, "build_opener") as build:
                build.return_value.open.return_value = self.response(b'{}', status, url)
                with self.assertRaises(guard.ReleaseBlocked) as caught:
                    guard.request_json(self.url, f"Bearer {TOKEN}")
                self.assertEqual(caught.exception.reason, "redirect")

    def test_transport_rejects_wrong_origin_before_sending_credentials(self):
        with patch.object(guard, "build_opener") as build:
            for url in ("http://ghcr.io/v2/", "https://ghcr.io.evil/v2/", "https://user@ghcr.io/v2/",
                        "https://ghcr.io:443/v2/", "https://ghcr.io/v2/#fragment"):
                with self.subTest(url=url), self.assertRaises(guard.ReleaseBlocked):
                    guard.request_json(url, f"Bearer {TOKEN}")
            build.assert_not_called()

    def test_transport_exception_is_sanitized(self):
        with patch.object(guard, "build_opener") as build:
            build.return_value.open.side_effect = URLError(f"Authorization: Bearer {TOKEN}")
            with self.assertRaises(guard.ReleaseBlocked) as caught:
                guard.request_json(self.url, f"Bearer {TOKEN}")
            self.assertNotIn(TOKEN, str(caught.exception))
            self.assertTrue(caught.exception.__suppress_context__)


if __name__ == "__main__":
    unittest.main()
