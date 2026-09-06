"""Refuse GHCR version replacement; uncertain registry responses fail closed."""
import base64
import json
import os
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ReleaseBlocked(Exception):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(url, authorization, accept="application/json"):
    request = Request(url, headers={"Authorization": authorization, "Accept": accept})
    try:
        with build_opener(NoRedirects()).open(request, timeout=30) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        # Never expose response bodies, URLs, or authorization in diagnostics.
        try:
            return error.code, json.load(error)
        except (ValueError, UnicodeError):
            raise ReleaseBlocked("Registry returned an unreadable error response.") from None


def require_unused_tag(image, version, actor, credential, request=request_json):
    if not re.fullmatch(r"ghcr\.io/[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._/-]*", image):
        raise ReleaseBlocked("Expected a lowercase GHCR image repository.")
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version):
        raise ReleaseBlocked("Expected vMAJOR.MINOR.PATCH.")
    if not actor or not credential:
        raise ReleaseBlocked("GitHub authentication is required.")
    repository = image.removeprefix("ghcr.io/")
    basic = base64.b64encode(f"{actor}:{credential}".encode()).decode()
    query = urlencode({"service": "ghcr.io", "scope": f"repository:{repository}:pull"})
    status, payload = request(f"https://ghcr.io/token?{query}", f"Basic {basic}")
    token = payload.get("token") if isinstance(payload, dict) else None
    if status != 200 or not isinstance(token, str) or not token.strip():
        raise ReleaseBlocked("Cannot authenticate registry read access.")
    authorization = f"Bearer {token}"
    # A bare 404 can hide denied access. First establish access to this package.
    status, payload = request(f"https://ghcr.io/v2/{repository}/tags/list?n=1", authorization)
    if (status != 200 or not isinstance(payload, dict)
            or payload.get("name") != repository
            or not isinstance(payload.get("tags"), list)):
        raise ReleaseBlocked("Cannot establish access to the existing image repository.")
    accept = ", ".join((
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    ))
    status, payload = request(
        f"https://ghcr.io/v2/{repository}/manifests/{version}", authorization, accept)
    if status == 200:
        raise ReleaseBlocked("Version image tag already exists; select a new version.")
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if (status != 404 or not isinstance(errors, list) or not errors
            or any(not isinstance(error, dict) or error.get("code") != "MANIFEST_UNKNOWN"
                   for error in errors)):
        raise ReleaseBlocked("Cannot reliably determine whether the version tag exists.")


def main():
    try:
        require_unused_tag(os.environ.get("IMAGE", ""), os.environ.get("GITHUB_REF_NAME", ""),
                           os.environ.get("GITHUB_ACTOR", ""), os.environ.get("GITHUB_TOKEN", ""))
    except Exception:
        # Network/library exceptions may contain sensitive response data.
        print("Release blocked: version exists or registry status is uncertain.", file=sys.stderr)
        return 1
    print("Version tag is absent in the accessible image repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
