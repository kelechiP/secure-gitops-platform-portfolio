# Software supply-chain security

## Scope and threat model

The release path gates publication on CI input pins, tag ancestry, version availability, and vulnerability scanning. Attestation and signing occur after publication, so a failure can leave a published image without those guarantees. It trusts GitHub-hosted runners, GitHub Actions, GHCR, GitHub OIDC, Sigstore, and the reviewed upstream Action commits. It does not provide admission enforcement, reproducible builds, or protection from a malicious maintainer authorized to create tags.

No cloud infrastructure, cloud credential, long-lived signing key, personal access token, or automatic GitOps commit is created by the release workflow.

## Release status

The sanitized portfolio repository is public, with protected `main` and protected `v*` release tags. Anonymous HTTPS repository access is available without credentials. The separately authorized `v0.1.0` container release completed successfully and is anonymously pullable from its public GHCR package. Provenance, SBOM attestation, and keyless Cosign signing and verification succeeded for the exact image digest. The [verified first-release record](verified-first-release.md) lists the version, commit, digest, workflow, package, SPDX inventory, identity constraints, reviewer commands, and seven-day evidence retention. No GitHub Release object was created.

First-package bootstrap was exercised successfully with the release job's scoped token under the narrow conditions below. Ordinary local and CI SPDX generation still do not constitute publication or attestation. Public visibility enables [artifact-attestation eligibility on applicable GitHub plans](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations), but does not guarantee success for future runs. Future releases require separate authorization. AWS/EKS remains a non-deployed static blueprint; live Argo CD reconciliation, monitoring, HPA behavior, and NetworkPolicy enforcement remain unvalidated.

## CI and release responsibilities

`.github/workflows/ci.yml` runs for pull requests and pushes to `main` with read-only permissions. It tests Python, renders Helm, rejects ambiguous image configuration, scans the image and Git history, statically validates the non-deployed Terraform foundation, and rejects mutable `uses:` references. It cannot publish packages, request OIDC tokens, create attestations, sign images, or access AWS.

`.github/workflows/release.yml` runs only for pushed `v*.*.*` tags and immediately enforces exact `vMAJOR.MINOR.PATCH` syntax. It resolves annotated and lightweight tags to their event commit, explicitly fetches `origin/main`, and requires `git merge-base --is-ancestor` to prove that commit is reachable from `origin/main` before registry login, publication, attestation, or signing. This prevents accidental releases from unmerged branches; it does not protect against a malicious authorized maintainer who can modify `main` or the release workflow and create tags. The release job alone receives `contents: read`, `packages: write`, `id-token: write`, and `attestations: write`. Pull requests cannot trigger it.

The workflow builds one local image with semantic-version and full-commit tags; it does not create `latest`. Trivy scans for applicable HIGH and CRITICAL vulnerabilities and Anchore generates an SPDX JSON SBOM, which must pass SPDX-version and nonempty-inventory validation before registry login or publication. After these gates succeed, the job uses its scoped `GITHUB_TOKEN` to push both tags. It resolves the registry digest and uses that immutable digest for GitHub build provenance, SPDX SBOM attestation, keyless Cosign signing, and verification against the exact workflow identity and GitHub OIDC issuer. The SBOM and attestation bundles are uploaded for seven days when the preceding steps succeed.

## Version immutability and artifact retention

Before Buildx setup, image build, registry login, publication, signing, or attestation, `scripts/check_release_tag.py` exchanges the release job's scoped `GITHUB_TOKEN` for a GHCR pull token. Credentials are passed through environment variables and HTTPS authorization headers, never command-line arguments or operator output. No PAT, new secret, or signing key is needed. Requests use only `https://ghcr.io`, reject redirects (including same-host redirects), use 30-second socket connection/read timeouts, and cap each JSON response at 1 MiB. Duplicate JSON keys and nonstandard JSON constants are rejected.

Only two outcomes permit continuation after an HTTP 200 token exchange with a nonempty valid bearer token:

1. **Package absent:** authenticated `GET /v2/<repository>/tags/list?n=1` returns HTTP 404 with a nonempty canonical `errors` array containing only exact `NAME_UNKNOWN` codes. No manifest lookup is needed for this case.
2. **Package exists, version absent:** the tag-list request returns HTTP 200 with the exact repository name and a valid list of tag strings; the exact version manifest then returns HTTP 404 with only canonical `MANIFEST_UNKNOWN` errors. Enumeration is an access/existence probe, not a complete paginated inventory; the manifest lookup is authoritative for the requested version. A requested version seen in the first page is blocked immediately.

An existing manifest, denied authentication/authorization, wrong or mixed error codes, malformed or empty JSON, unexpected response shape/status, redirect, timeout, or network error blocks release. Output distinguishes package absence, version absence, existing version, authentication/authorization failure, and unknown failure without exposing response bodies or credentials. The [Distribution API](https://distribution.github.io/distribution/spec/api/) defines `NAME_UNKNOWN` as an unknown repository and `MANIFEST_UNKNOWN` as an unknown manifest. The [GHCR authentication documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) supports scoped workflow `GITHUB_TOKEN` use. These are strict accepted protocol conditions, not a claim that every absent GHCR package returns them: if token acquisition is denied or GHCR masks absence, bootstrap remains blocked. Mocked tests do not prove live GHCR token permissions or visibility behavior.

The repository-wide `release-${{ github.repository }}` concurrency group serializes all release executions, including different version tags, without cancelling an in-progress run. GitHub may replace a pending run when another is queued; this is not a durable release queue. The guard and publication stay within the same workflow concurrency boundary. Authorized registry administrators and alternative publishing mechanisms remain outside it, so this does not eliminate every check-to-push race. The full-commit reference can still be reused for a new semantic version; semantic-version reruns are refused.

Tag protections separately prohibit updates and deletion of `v*` tags without bypass. An administrator-only creation rule permits a deliberately authorized future tag; its creation exception does not bypass immutability. This change does not alter those settings. A sole owner can merge a compliant PR with zero approvals, but cannot bypass the required PR, CI, and conversation-resolution gates under the current branch protection.

Future CI and release Buildx records and release evidence have explicit seven-day retention. Gitleaks' default artifact upload is disabled only to replace it with one seven-day SARIF upload that also runs after scan failure when a report exists; scanning, summaries, and the failure gate remain enabled. No SBOM artifact is retained by the CI generation check; it is validated on the runner without publication.

## Current Distroless base pin

The Dockerfile pins `gcr.io/distroless/python3-debian13:nonroot` to official index digest `sha256:1c32c3720dc4c7f0c7dbe998737f32c200add6511eca7cec705008be488b87d6`, independently resolved from the official `gcr.io/distroless/python3-debian13` registry on 2026-11-07. Its `linux/amd64` child is `sha256:f7f5ca4fd8d9b2d7f70a436da50d2051ab30468c9055eea5597b61286061efea`. The index also supports arm64 and riscv64; the application build remains single-platform. The amd64 image runs as UID 65532 with `/usr/bin/python3.13` as its entrypoint. Application startup, non-root ownership, and runtime security settings are unchanged; no shell or package manager is added.

The preceding base produced Trivy failures in the Action-only dependency PRs. Their October scans reported two fixable HIGH OpenSSL findings; the November scans reported six fixable HIGH findings: five in `libexpat1` (CVE-2026-66046, CVE-2026-76956, CVE-2026-76957, CVE-2026-77214, CVE-2026-93990) and one in `libssl3t64` (CVE-2026-84782). The updated base passed the unchanged container gate in the digest-update PR and in the local 2026-11-07 scan (zero applicable HIGH/CRITICAL findings). The gate continues to reject applicable HIGH/CRITICAL findings while excluding unfixed vulnerabilities under the existing policy; findings can change as vulnerability data evolves.

The readable tag explains runtime intent; the digest fixes the base bytes despite tag movement. Reviewed digest updates remain necessary for security fixes. Pinning does not establish bit-for-bit reproducible builds.

### Historical release boundary

This current dependency inventory describes the proposed inputs for future builds, not the inputs that produced `v0.1.0`. That release used index `sha256:8ee214843129f43e2ebf5e0ca9f2e4e6d8292143d1b8a6787f169b5898578884` and amd64 child `sha256:359614ec673d26ff9f9de9edabe2e6764a45a97a7791f309e5dca218c5a18295`. Its original Action pins remain available in the [release workflow at the release commit](https://github.com/kelechiP/secure-gitops-platform-portfolio/blob/e14533f30681c4d3783c4de55b03c6072a3884fb/.github/workflows/release.yml). The [verified release record](verified-first-release.md), tag, published image, and signed evidence are unchanged. Dependency maintenance does not rebuild or repair an already-published image; any future release needs separate authorization.

## Current immutable Action inventory

The five November updates below were independently resolved from official upstream release tags on 2026-11-07. Other pins retain their prior review (2026-08-23, with Anchore v0.24.2 reviewed on 2026-09-05). This table matches current workflow configuration; it is not the historical release inventory. Version comments are informational; GitHub executes the full SHA.

| Action | Version | Commit SHA | Official upstream |
|---|---|---|---|
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | https://github.com/actions/checkout |
| `actions/setup-python` | v7.1.0 | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | https://github.com/actions/setup-python |
| `azure/setup-helm` | v5.0.1 | `9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310` | https://github.com/Azure/setup-helm |
| `docker/setup-buildx-action` | v4.4.1 | `f87e5991a6d7451dcb8d9637bfbc97413f497069` | https://github.com/docker/setup-buildx-action |
| `docker/build-push-action` | v7.4.0 | `c3c9e263c25d99ce0380d002d59b67737d91b0dc` | https://github.com/docker/build-push-action |
| `aquasecurity/trivy-action` | v0.36.0 | `ed142fd0673e97e23eac54620cfb913e5ce36c25` | https://github.com/aquasecurity/trivy-action |
| `gitleaks/gitleaks-action` | v3.0.0 | `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` | https://github.com/gitleaks/gitleaks-action |
| `docker/login-action` | v4.6.0 | `dbcb813823bdd20940b903addbd779551569679f` | https://github.com/docker/login-action |
| `anchore/sbom-action` | v0.24.2 | `3ad7283483fc7af8ff2b4ea19663c2d5ca935e26` | https://github.com/anchore/sbom-action |
| `actions/attest-build-provenance` | v4.2.2 | `4d101475d8b20a2381f78447822ac1eab6504dd8` | https://github.com/actions/attest-build-provenance |
| `actions/attest` | v4.2.2 | `1e69f48acb82d1966a394da916b4c1698aa569d6` | https://github.com/actions/attest |
| `sigstore/cosign-installer` | v4.1.2 | `6f9f17788090df1f26f669e9d70d6ae9567deba6` | https://github.com/sigstore/cosign-installer |
| `actions/upload-artifact` | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` | https://github.com/actions/upload-artifact |
| `hashicorp/setup-terraform` | v4.0.1 | `dfe3c3f87815947d99a8997f908cb6525fc44e9e` | https://github.com/hashicorp/setup-terraform |
| `terraform-linters/setup-tflint` | v6.3.2 | `6ffdbaa3be476b3431f7275c26966ef32ff60337` | https://github.com/terraform-linters/setup-tflint |

November release-note review:

- [Build/push v7.4.0](https://github.com/docker/build-push-action/releases/tag/v7.4.0) prevents workflow-command injection in metadata logs, adopts shared Buildx error handling, and refreshes dependencies.
- [Buildx v4.4.0](https://github.com/docker/setup-buildx-action/releases/tag/v4.4.0) uses official releases for the cloud driver and pre-pulls BuildKit; [v4.4.1](https://github.com/docker/setup-buildx-action/releases/tag/v4.4.1) skips that pre-pull for explicit endpoints. This repository uses the default builder path.
- [Python v7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0) adds optional mirror/mirror-token inputs, improves errors, and refreshes cache and dependencies. No custom mirror or credential is enabled here.
- [Artifact v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2) improves HTTP 429 retries and Retry-After handling via its artifact dependency; seven-day retention remains unchanged.
- [TFLint setup v6.3.2](https://github.com/terraform-linters/setup-tflint/releases/tag/v6.3.2) builds its distribution on release and requires a semantic-version TFLint input. The existing `v0.64.0` input satisfies that requirement; the TFLint binary version is unchanged.

No reviewed release note requires additional workflow permissions. PR permissions remain read-only, and package/OIDC/attestation writes remain confined to the release job. No unrelated Actions, release gates, signing identities, concurrency settings, or publication behavior are changed.

`scripts/validate_action_pins.py` checks Actions and reusable workflows in `.yml` and `.yaml` files. It accepts local Actions, full 40-character remote commits, and Docker Actions pinned by `sha256`; it rejects tags, branches, abbreviated SHAs, and tag-based Docker Actions. Unit tests cover job- and step-level syntax, quotes, and trailing comments.

## Release verification

The [verified first-release record](verified-first-release.md#reviewer-verification-commands) contains exact commands for `v0.1.0`, including source commit/ref and certificate identity constraints for GitHub attestations, Cosign verification, and anonymous registry checks.

Each future release requires separate authorization to select an unused semantic version and create/push its tag from reviewed `main`. Do not bypass uncertain registry results, rerun publication to overwrite an existing version, or move/delete a release tag. Package visibility is independent of repository visibility and must be checked. A failure after publication may leave an image without complete evidence; a new version requires new authorization. Digest-based GitOps promotion remains separate reviewed work.

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

- Publication and independent evidence verification are established only for the recorded `v0.1.0` digest; they do not guarantee future releases or deployment enforcement.
- GitHub and Sigstore availability and policy are external dependencies.
- The base digest fixes one build input; it does not establish bit-for-bit reproducibility.
- The release is single-platform; no multi-architecture manifest is produced.
- Trivy ignores vulnerabilities with no fix, matching existing CI policy; they still require monitoring.
- Kubernetes has no signature admission policy, so verification is not cluster-enforced.
- Immutable Action pins require reviewed updates to receive upstream security fixes.
