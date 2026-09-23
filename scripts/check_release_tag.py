"""Permit only authenticated, canonical GHCR absence; uncertainty blocks release."""
import base64
import json
import os
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 1024 * 1024
MESSAGES = {
    "input": "Expected a lowercase GHCR repository and exact vMAJOR.MINOR.PATCH.",
    "auth": "Registry authentication or authorization failed.",
    "exists": "Version image tag already exists; select a new version.",
    "redirect": "Registry redirect rejected.",
    "unknown": "Registry status is uncertain; publication is blocked.",
}
RESULTS = {
    "package_absent": "Package is absent (authenticated NAME_UNKNOWN); first-package bootstrap permitted.",
    "version_absent": "Package exists; requested version is absent (authenticated MANIFEST_UNKNOWN).",
}


class ReleaseBlocked(Exception):
    def __init__(self, reason="unknown"):
        # Only fixed messages may cross the operator-output boundary.
        self.reason = reason if reason in MESSAGES else "unknown"
        super().__init__(MESSAGES[self.reason])


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Nonstandard JSON constant")


def check_status(status):
    if type(status) is not int:
        raise ReleaseBlocked()
    if status in (401, 403):
        raise ReleaseBlocked("auth")
    if 300 <= status < 400:
        raise ReleaseBlocked("redirect")
    if status not in (200, 404):
        raise ReleaseBlocked()


def request_json(url, authorization, accept="application/json"):
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "ghcr.io" or parsed.fragment:
            raise ReleaseBlocked("input")
        request = Request(url, headers={"Authorization": authorization, "Accept": accept})
        try:
            response = build_opener(NoRedirects()).open(request, timeout=TIMEOUT_SECONDS)
        except HTTPError as error:
            response = error
        with response:
            # Defense in depth: even a replaced transport must not return another URL.
            if response.geturl() != url:
                raise ReleaseBlocked("redirect")
            check_status(response.code)
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ReleaseBlocked()
            payload = json.loads(body.decode("utf-8"), object_pairs_hook=unique_object,
                                 parse_constant=reject_constant)
            return response.code, payload
    except ReleaseBlocked:
        raise
    except Exception:
        # Library failures can contain credentials or server-controlled material.
        raise ReleaseBlocked() from None


def canonical_error(payload, code):
    if not isinstance(payload, dict) or set(payload) != {"errors"}:
        return False
    errors = payload["errors"]
    return (isinstance(errors, list) and bool(errors)
            and all(isinstance(error, dict) and error.get("code") == code
                    and set(error) <= {"code", "message", "detail"}
                    and ("message" not in error or isinstance(error["message"], str))
                    for error in errors))


def require_unused_tag(image, version, actor, credential, request=request_json):
    component = r"[a-z0-9]+(?:[._-][a-z0-9]+)*"
    if (not re.fullmatch(rf"ghcr\.io/{component}(?:/{component})+", image)
            or not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version)):
        raise ReleaseBlocked("input")
    if not actor or not credential or any(c in actor for c in ":\r\n"):
        raise ReleaseBlocked("auth")

    def query(url, authorization, accept="application/json"):
        try:
            status, payload = request(url, authorization, accept)
        except ReleaseBlocked:
            raise
        except Exception:
            raise ReleaseBlocked() from None
        check_status(status)
        return status, payload

    repository = image.removeprefix("ghcr.io/")
    basic = base64.b64encode(f"{actor}:{credential}".encode()).decode()
    parameters = urlencode({"service": "ghcr.io", "scope": f"repository:{repository}:pull"})
    status, payload = query(f"https://ghcr.io/token?{parameters}", f"Basic {basic}")
    token = payload.get("token") if isinstance(payload, dict) else None
    if (status != 200 or not isinstance(payload, dict) or "errors" in payload
            or not isinstance(token, str)
            or not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token)):
        raise ReleaseBlocked("auth")
    authorization = f"Bearer {token}"
    status, payload = query(f"https://ghcr.io/v2/{repository}/tags/list?n=1", authorization)
    if status == 404 and canonical_error(payload, "NAME_UNKNOWN"):
        return "package_absent"
    if (status != 200 or not isinstance(payload, dict) or "errors" in payload
            or payload.get("name") != repository or not isinstance(payload.get("tags"), list)
            or any(not isinstance(tag, str) or not re.fullmatch(r"[\w][\w.-]{0,127}", tag, re.ASCII)
                   for tag in payload["tags"])):
        raise ReleaseBlocked()
    if version in payload["tags"]:
        raise ReleaseBlocked("exists")
    accept = ", ".join((
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    ))
    status, payload = query(
        f"https://ghcr.io/v2/{repository}/manifests/{version}", authorization, accept)
    if status == 200:
        raise ReleaseBlocked("exists")
    if status == 404 and canonical_error(payload, "MANIFEST_UNKNOWN"):
        return "version_absent"
    raise ReleaseBlocked()


def main():
    try:
        result = require_unused_tag(
            os.environ.get("IMAGE", ""), os.environ.get("GITHUB_REF_NAME", ""),
            os.environ.get("GITHUB_ACTOR", ""), os.environ.get("GITHUB_TOKEN", ""))
    except ReleaseBlocked as error:
        print(f"Release blocked: {MESSAGES[error.reason]}", file=sys.stderr)
        return 1
    except Exception:
        print(f"Release blocked: {MESSAGES['unknown']}", file=sys.stderr)
        return 1
    print(RESULTS[result])
    return 0


if __name__ == "__main__":
    sys.exit(main())
