# Verified first container release

## Release record

The separately authorized `v0.1.0` container release completed and was independently verified on 2026-09-24 (UTC). This is a Git tag and GHCR container release; no GitHub Release object was created.

| Item | Verified value |
|---|---|
| Version | `v0.1.0` |
| Release commit | `e14533f30681c4d3783c4de55b03c6072a3884fb` |
| Annotated tag object | `179dfbcc121759c2f885a1dbcd037d3f894ea464` |
| Image digest | `sha256:2332bac5c9ad7abc7de0cbf9b8dc9dbe0777ec5fb8aa5b3c2831187ea2a3c5a9` |
| Release workflow | [Run 35939384855](https://github.com/kelechiP/secure-gitops-platform-portfolio/actions/runs/35939384855), `release` job successful |
| Package | [secure-gitops-platform-portfolio](https://github.com/users/kelechiP/packages/container/package/secure-gitops-platform-portfolio), public and associated with this repository |
| Version image | `ghcr.io/kelechip/secure-gitops-platform-portfolio:v0.1.0` |
| Commit image | `ghcr.io/kelechip/secure-gitops-platform-portfolio:e14533f30681c4d3783c4de55b03c6072a3884fb` |
| SPDX SBOM | SPDX 2.3, 39 packages; generated and validated before publication |
| Provenance | GitHub verification succeeded for `https://slsa.dev/provenance/v1` and the exact image digest |
| SBOM attestation | GitHub verification succeeded; signed predicate is `https://spdx.dev/Document/v2.3` and equals the downloaded SPDX document |
| Signature | Keyless Cosign signing and workflow verification succeeded; independent Cosign verification also succeeded |
| Anonymous access | Manifest queries and Docker pull succeeded with no registry credentials |
| `latest` | Not published; manifest query returned HTTP 404 with `MANIFEST_UNKNOWN` |

Both image tags resolved to the same canonical digest, and hashing the anonymous manifest response independently matched its `Docker-Content-Digest` header. The tag resolves to the release commit reachable from `origin/main`. The main CI run passed all five required jobs before tag creation.

The release guard observed successful token acquisition followed by authenticated HTTP 404 `NAME_UNKNOWN` from tag enumeration. The workflow built the application image once, passed its existing vulnerability gate, generated and validated the SBOM, and only then published both image tags. Provenance, SBOM attestation, signing, and verification all addressed the exact digest above. No workflow rerun or alternate version was needed.

## Identity and retained evidence

Verification enforced this exact certificate identity:

`https://github.com/kelechiP/secure-gitops-platform-portfolio/.github/workflows/release.yml@refs/tags/v0.1.0`

The OIDC issuer was `https://token.actions.githubusercontent.com`. Independent GitHub verification also enforced the source commit, tag ref, repository, and GitHub-hosted runner requirement. Independent Cosign verification checked the certificate chain, transparency-log evidence, claims, and image digest. Verification used GitHub CLI 2.96.0 and Cosign 3.1.3.

The workflow uploaded `supply-chain-evidence-v0.1.0`, containing the SPDX document and both attestation bundles, at 2026-09-24 00:40:54 UTC, with expiration 2026-10-01 00:40:54 UTC (seven days). Its Buildx record has the same seven-day retention policy. Downloaded evidence is not committed to Git. Artifact expiration does not extend because these instructions are retained; reviewers can also query the published attestations while they remain available.

## Reviewer verification commands

Prerequisites: Git, Docker with a running daemon, GitHub CLI with repository/attestation read access, and Cosign. The commands verify existing artifacts only; they do not rebuild, publish, sign, create tags, or deploy infrastructure.

```powershell
$image = 'ghcr.io/kelechip/secure-gitops-platform-portfolio'
$commit = 'e14533f30681c4d3783c4de55b03c6072a3884fb'
$digest = 'sha256:2332bac5c9ad7abc7de0cbf9b8dc9dbe0777ec5fb8aa5b3c2831187ea2a3c5a9'
$identity = 'https://github.com/kelechiP/secure-gitops-platform-portfolio/.github/workflows/release.yml@refs/tags/v0.1.0'
$issuer = 'https://token.actions.githubusercontent.com'

git ls-remote --tags https://github.com/kelechiP/secure-gitops-platform-portfolio.git 'refs/tags/v0.1.0' 'refs/tags/v0.1.0^{}'
gh run view 35939384855 --repo kelechiP/secure-gitops-platform-portfolio --json headSha,conclusion,jobs

# Empty Docker configuration demonstrates anonymous pulling without changing login state.
$anonymousConfig = Join-Path ([IO.Path]::GetTempPath()) ('portfolio-anonymous-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $anonymousConfig | Out-Null
[IO.File]::WriteAllText((Join-Path $anonymousConfig 'config.json'), '{}')
docker --config $anonymousConfig pull "${image}@${digest}"
if ($LASTEXITCODE -ne 0) { throw 'Anonymous image pull failed' }

gh attestation verify "oci://${image}@${digest}" --repo kelechiP/secure-gitops-platform-portfolio --predicate-type https://slsa.dev/provenance/v1 --cert-identity $identity --cert-oidc-issuer $issuer --source-digest $commit --source-ref refs/tags/v0.1.0 --deny-self-hosted-runners --format json
if ($LASTEXITCODE -ne 0) { throw 'Provenance verification failed' }

gh attestation verify "oci://${image}@${digest}" --repo kelechiP/secure-gitops-platform-portfolio --predicate-type https://spdx.dev/Document --cert-identity $identity --cert-oidc-issuer $issuer --source-digest $commit --source-ref refs/tags/v0.1.0 --deny-self-hosted-runners --format json
if ($LASTEXITCODE -ne 0) { throw 'SBOM attestation verification failed' }

cosign verify --certificate-identity $identity --certificate-oidc-issuer $issuer "${image}@${digest}"
if ($LASTEXITCODE -ne 0) { throw 'Cosign verification failed' }
```

For independent anonymous checks of both tags and the absence of `latest`, run this Python script. The token is anonymous, remains in memory, and is never printed:

```python
import hashlib
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

repository = "kelechip/secure-gitops-platform-portfolio"
commit = "e14533f30681c4d3783c4de55b03c6072a3884fb"
expected = "sha256:2332bac5c9ad7abc7de0cbf9b8dc9dbe0777ec5fb8aa5b3c2831187ea2a3c5a9"
with urlopen("https://ghcr.io/token?service=ghcr.io&scope=repository:" + repository + ":pull", timeout=30) as response:
    token = json.load(response)["token"]
accept = ", ".join(("application/vnd.oci.image.manifest.v1+json",
                    "application/vnd.oci.image.index.v1+json",
                    "application/vnd.docker.distribution.manifest.v2+json",
                    "application/vnd.docker.distribution.manifest.list.v2+json"))
for tag in ("v0.1.0", commit, "latest"):
    request = Request("https://ghcr.io/v2/" + repository + "/manifests/" + tag,
                      headers={"Authorization": "Bearer " + token, "Accept": accept})
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            assert tag != "latest", "Unexpected latest tag"
            assert response.headers["Docker-Content-Digest"] == expected
            assert "sha256:" + hashlib.sha256(body).hexdigest() == expected
            print(tag, expected)
    except HTTPError as error:
        errors = json.load(error).get("errors")
        assert tag == "latest" and error.code == 404
        assert errors and all(item.get("code") == "MANIFEST_UNKNOWN" for item in errors)
        print("latest absent: authenticated anonymous-token query returned MANIFEST_UNKNOWN")
```

## Boundaries and remaining limitations

No AWS resources, Terraform deployment, Kubernetes resources, or Argo CD deployment were created. GitOps desired-state image references were not changed. Live reconciliation, monitoring, HPA behavior, and NetworkPolicy enforcement remain unvalidated. The original private repository and its package metadata/versions were unchanged by this release.

The Helm default still selects `latest`, which intentionally does not exist. Any future deployment must separately review and select a verified digest (clearing `image.tag`), or a deliberate version; this documentation does not perform that promotion. The local GitOps examples still use the locally loaded image.

The image is single-platform. Passing Trivy applies the existing HIGH/CRITICAL gate with unfixed vulnerabilities excluded; it is not a claim that no vulnerability exists. Attestations bind claims to this digest and workflow identity, not proof of reproducible builds or cluster admission enforcement. Authorized alternative registry publishers remain outside workflow concurrency. Future versions require separate authorization; never move, delete, or reuse `v0.1.0` to repair a later failure.
