# Secure GitOps Portfolio Platform

[![CI](https://github.com/kelechiP/secure-gitops-platform-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/kelechiP/secure-gitops-platform-portfolio/actions/workflows/ci.yml)

A DevOps and DevSecOps reference platform combining a minimal Python service, hardened containers, Kubernetes delivery with Helm and Argo CD, observability, and a static AWS/EKS Terraform blueprint.

## Architecture

```mermaid
flowchart LR
    Code[Source changes] --> CI[Tests and security gates]
    CI --> Image[Local image and SPDX SBOM]
    Git[Reviewed GitOps configuration] --> Argo[Argo CD]
    Argo --> K8s[Local Kubernetes]
    K8s --> Metrics[Prometheus and Grafana]
    Release[Authorized container release] --> Registry[Verified GHCR image]
```

## Engineering focus

- Dependency-free HTTP API with health, readiness, and Prometheus metrics endpoints.
- Non-root Distroless runtime pinned by immutable digest.
- Helm security defaults: read-only root filesystem, dropped capabilities, seccomp, resource bounds, and no service-account token mount.
- Argo CD HTTPS manifests with limited AppProjects, pruning, and self-healing configuration.
- Prometheus discovery, a Grafana dashboard, and a target-availability alert rule.
- Read-only CI for tests, Helm, Terraform, secret detection, vulnerability scanning, and SPDX SBOM generation.
- Full commit-SHA pins for GitHub Actions, release concurrency protection, and a fail-closed version-tag guard.
- Validated static Terraform blueprint for private EKS workers, encrypted storage, restricted endpoints, KMS, and control-plane logging. AWS/EKS has not been deployed.

## Run the application

```powershell
python -m unittest discover -s app/tests -v
python app/src/server.py
```

The service listens on port 8080. Endpoints are `/`, `/healthz`, `/readyz`, and `/metrics`.

For a local container:

```powershell
docker build -t secure-gitops-platform-portfolio:local ./app
docker run --rm -p 127.0.0.1:8080:8080 --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m --security-opt no-new-privileges secure-gitops-platform-portfolio:local
```

## Validate the platform

```powershell
python -m unittest discover -s scripts/tests -v
python scripts/validate_action_pins.py
helm lint helm/platform-api
helm template platform-api helm/platform-api --namespace secure-platform
terraform -chdir=infra/terraform/aws init -backend=false -input=false
terraform -chdir=infra/terraform/aws validate
```

See [local validation](docs/local-validation.md), [architecture](docs/architecture.md), and the [Terraform blueprint](infra/terraform/aws/README.md) for scope and further checks.

## GitOps and observability

The Applications target `https://github.com/kelechiP/secure-gitops-platform-portfolio.git`. This sanitized portfolio repository is public and anonymous HTTPS access is available without a repository credential. Live reconciliation remains unvalidated and requires separate authorization. No Kubernetes deployment was performed to initialize this repository.

The local workflow uses a locally built image loaded into kind. The published portfolio image is anonymously pullable, but the Helm default still selects the intentionally absent `latest` tag. A future deployment must separately select a verified digest or deliberate version; no GitOps image reference was changed. See the [GitOps guide](docs/argocd-validation.md) and [observability guide](docs/observability.md) for future validation procedures.

## Release status

The separately authorized `v0.1.0` container release succeeded. Both its version and full-commit tags resolve to `sha256:2332bac5c9ad7abc7de0cbf9b8dc9dbe0777ec5fb8aa5b3c2831187ea2a3c5a9`. Anonymous pulling, GitHub provenance and SBOM attestations, and keyless Cosign signature verification passed independently. The SPDX 2.3 SBOM contains 39 packages. `latest` was not published.

See the [verified release record and reviewer commands](docs/verified-first-release.md) for the release commit, workflow, public package, evidence retention, and limitations. The repository retains protected `main` and protected `v*` tags. No infrastructure was deployed; future releases and GitOps promotion require separate authorization. Ordinary CI SPDX generation alone does not establish the release's attestation guarantees. See [supply-chain security](docs/supply-chain-security.md).

## Scope and limitations

Local tests and static checks validate the source, templates, and container. Live GitOps reconciliation, monitoring, HPA scaling, and NetworkPolicy enforcement have not been validated from this repository. HPA needs Metrics Server; NetworkPolicy needs a compatible CNI. AWS remains a non-deployed static blueprint. Admission policy, SLOs, and progressive delivery are on the [roadmap](docs/roadmap.md).

## Repository layout

| Directory | Purpose |
|---|---|
| `app/` | API, tests, and Dockerfile |
| `helm/platform-api/` | Workload and monitoring templates |
| `gitops/clusters/local/` | Argo CD projects and applications |
| `observability/` | Monitoring values and dashboard |
| `infra/terraform/aws/` | Static AWS/EKS blueprint |
| `scripts/` | Validation and local workflow helpers |
| `.github/workflows/` | CI and separately authorized release workflow |

Licensed under the [MIT License](LICENSE).
