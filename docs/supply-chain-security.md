# Software supply-chain security

## Scope and threat model

The release path gates publication on CI input pins, tag ancestry, version availability, and vulnerability scanning. Attestation and signing occur after publication, so a failure can leave a published image without those guarantees. It trusts GitHub-hosted runners, GitHub Actions, GHCR, GitHub OIDC, Sigstore, and the reviewed upstream Action commits. It does not provide admission enforcement, reproducible builds, or protection from a malicious maintainer authorized to create tags.

No cloud infrastructure, cloud credential, long-lived signing key, personal access token, or automatic GitOps commit is created by the release workflow.

## Release status

No release has been published from this repository and no GHCR package exists yet. The future image repository is `ghcr.io/kelechip/secure-gitops-platform-portfolio`. Local and CI SPDX SBOM generation do not constitute publication or attestation. Provenance, SBOM attestation, signing, and signature verification remain unvalidated. A first release requires separate authorization.

The release guard fails closed when the package does not exist. First-package bootstrap is intentionally deferred and requires a separately reviewed design before any version tag is authorized. Repository visibility alone does not guarantee successful attestation or signing.

## CI and release responsibilities

`.github/workflows/ci.yml` runs for pull requests and pushes to `main` with read-only permissions. It tests Python, renders Helm, rejects ambiguous image configuration, scans the image and Git history, statically validates the non-deployed Terraform foundation, and rejects mutable `uses:` references. It cannot publish packages, request OIDC tokens, create attestations, sign images, or access AWS.

`.github/workflows/release.yml` runs only for pushed `v*.*.*` tags and immediately enforces exact `vMAJOR.MINOR.PATCH` syntax. It resolves annotated and lightweight tags to their event commit, explicitly fetches `origin/main`, and requires `git merge-base --is-ancestor` to prove that commit is reachable from `origin/main` before registry login, publication, attestation, or signing. This prevents accidental releases from unmerged branches; it does not protect against a malicious authorized maintainer who can modify `main` or the release workflow and create tags. The release job alone receives `contents: read`, `packages: write`, `id-token: write`, and `attestations: write`. Pull requests cannot trigger it.

The workflow builds one local image with semantic-version and full-commit tags; it does not create `latest`. Trivy scans for applicable HIGH and CRITICAL vulnerabilities and Anchore generates an SPDX JSON SBOM before registry login or publication. After both succeed, the job uses its scoped `GITHUB_TOKEN` to push both tags. It resolves the registry digest and uses that immutable digest for GitHub build provenance, SPDX SBOM attestation, keyless Cosign signing, and verification against the exact workflow identity and GitHub OIDC issuer. The SBOM and attestation bundles are uploaded for seven days when the preceding steps succeed.

## Version immutability and artifact retention

Before Buildx setup or any image build/push, `scripts/check_release_tag.py` exchanges the existing job-scoped `GITHUB_TOKEN` for GHCR pull access. It first requires successful access to the existing package's tag listing, then checks the exact semantic-version manifest. Only an authenticated HTTP 404 with `MANIFEST_UNKNOWN` permits continuation; an existing tag, denied access, unknown package, malformed response, redirect, timeout, or registry failure blocks release. No PAT or new secret is used, and credentials are never printed. The commit-SHA reference remains available for a genuinely new version.

Workflow concurrency serializes executions for the same Git ref without cancelling a running publication. Together these controls prevent ordinary version reruns and concurrent same-version replacement. Registry administration or alternative publishing workflows controlled by an authorized maintainer remain outside this boundary. An absent or inaccessible package intentionally blocks this guard; this repository's first publication requires separate review of its package bootstrap.

Future CI and release Buildx records and release evidence have explicit seven-day retention. Gitleaks' default artifact upload is disabled only to replace it with one seven-day SARIF upload that also runs after scan failure when a report exists; scanning, summaries, and the failure gate remain enabled. No SBOM artifact is retained by the CI generation check; it is validated on the runner without publication.

## Distroless base pin

The Dockerfile pins `gcr.io/distroless/python3-debian13:nonroot` to official index digest `sha256:f3d5ddc6c64a019fe520e7f005f2880be21e6afc461b10a3c15ef2e4edc71e33`, resolved from `gcr.io` on 2026-09-05. Its `linux/amd64` child is `sha256:2da46b943456ad2544a03426474f593aacb6af587c64fa3229c7b16987bb30e2`. The index also contains arm64 and riscv64; the release remains single-platform on its hosted runner.

The readable tag explains runtime intent; the digest fixes the base bytes despite upstream tag movement. Non-root ownership, Python execution, and application behavior remain unchanged. Reviewed digest updates are needed for security fixes. This improves input reproducibility without claiming bit-for-bit reproducible builds. Focused tests reject removal or malformation of the base pin.

## Immutable Action inventory

Official release tags were resolved to these upstream commits on 2026-08-23; the Anchore v0.24.2 tag was independently resolved on 2026-09-05. Version comments are informational; GitHub executes the full SHA.

| Action | Version | Commit SHA | Official upstream |
|---|---|---|---|
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | https://github.com/actions/checkout |
| `actions/setup-python` | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` | https://github.com/actions/setup-python |
| `azure/setup-helm` | v5.0.1 | `9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310` | https://github.com/Azure/setup-helm |
| `docker/setup-buildx-action` | v4.3.0 | `37fe631027851001ddb9b187196cc803df7f5f0e` | https://github.com/docker/setup-buildx-action |
| `docker/build-push-action` | v7.3.0 | `53b7df96c91f9c12dcc8a07bcb9ccacbed38856a` | https://github.com/docker/build-push-action |
| `aquasecurity/trivy-action` | v0.36.0 | `ed142fd0673e97e23eac54620cfb913e5ce36c25` | https://github.com/aquasecurity/trivy-action |
| `gitleaks/gitleaks-action` | v3.0.0 | `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` | https://github.com/gitleaks/gitleaks-action |
| `docker/login-action` | v4.6.0 | `dbcb813823bdd20940b903addbd779551569679f` | https://github.com/docker/login-action |
| `anchore/sbom-action` | v0.24.2 | `3ad7283483fc7af8ff2b4ea19663c2d5ca935e26` | https://github.com/anchore/sbom-action |
| `actions/attest-build-provenance` | v4.2.2 | `4d101475d8b20a2381f78447822ac1eab6504dd8` | https://github.com/actions/attest-build-provenance |
| `actions/attest` | v4.2.2 | `1e69f48acb82d1966a394da916b4c1698aa569d6` | https://github.com/actions/attest |
| `sigstore/cosign-installer` | v4.1.2 | `6f9f17788090df1f26f669e9d70d6ae9567deba6` | https://github.com/sigstore/cosign-installer |
| `actions/upload-artifact` | v7.0.1 | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | https://github.com/actions/upload-artifact |
| `hashicorp/setup-terraform` | v4.0.1 | `dfe3c3f87815947d99a8997f908cb6525fc44e9e` | https://github.com/hashicorp/setup-terraform |
| `terraform-linters/setup-tflint` | v6.3.0 | `6e1e0642c0289bd619021bf6b34e3c08ed1e005a` | https://github.com/terraform-linters/setup-tflint |

`scripts/validate_action_pins.py` checks Actions and reusable workflows in `.yml` and `.yaml` files. It accepts local Actions, full 40-character remote commits, and Docker Actions pinned by `sha256`; it rejects tags, branches, abbreviated SHAs, and tag-based Docker Actions. Unit tests cover job- and step-level syntax, quotes, and trailing comments.

## Release verification

An authorized maintainer must review `main`, select an unused semantic version, and explicitly authorize creation and push of the tag. After a successful run, verify its captured digest:

```powershell
$image = "ghcr.io/kelechip/secure-gitops-platform-portfolio"
$digest = "sha256:<published-digest>"
cosign verify `
  --certificate-identity "https://github.com/kelechiP/secure-gitops-platform-portfolio/.github/workflows/release.yml@refs/tags/v1.2.3" `
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" `
  "${image}@${digest}"
gh attestation verify "oci://${image}@${digest}" --repo kelechiP/secure-gitops-platform-portfolio
```

These commands are examples for a future independently authorized release, not evidence of a published or verified image. Replace the example version and digest only after that release succeeds.

## Digest-based GitOps promotion and rollback

The chart remains backward compatible: `image.digest` defaults empty. Digest deployment requires clearing `image.tag`; setting both fails rendering. A digest must use the canonical `sha256:` prefix followed by exactly 64 lowercase hexadecimal characters; abbreviated, uppercase, malformed, and non-SHA256 values fail rendering.

```powershell
helm template platform-api helm/platform-api `
  --set image.repository=ghcr.io/kelechip/secure-gitops-platform-portfolio `
  --set image.tag= `
  --set image.digest=sha256:<published-digest>
```

A future reviewed promotion updates GitOps desired state to the GHCR repository and immutable digest. Record the semantic version in the promotion commit because `image.tag` must remain empty with a digest. Argo CD then reconciles that reviewed change. There is no automatic commit-back bot. Rollback reverts to a previously verified and retained digest; retagging cannot alter a digest-pinned workload.

## Remaining limitations

- Publication, provenance, SBOM attestation, signing, and signature verification remain unvalidated.
- GitHub and Sigstore availability and policy are external dependencies.
- The base digest fixes one build input; it does not establish bit-for-bit reproducibility.
- The release is single-platform; no multi-architecture manifest is produced.
- Trivy ignores vulnerabilities with no fix, matching existing CI policy; they still require monitoring.
- Kubernetes has no signature admission policy, so verification is not cluster-enforced.
- Immutable Action pins require reviewed updates to receive upstream security fixes.
