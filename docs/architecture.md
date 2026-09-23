# Architecture

The platform separates application delivery from cluster reconciliation:

1. GitHub Actions validates source, Kubernetes templates, secrets, and the container image.
2. A separately authorized release workflow is designed to publish a scanned image, then attempt provenance, SBOM attestation, and keyless signing.
3. GitOps configuration records the desired image and Helm values.
4. Argo CD detects desired-state changes and reconciles Kubernetes.
5. Kubernetes performs rolling updates and continuously evaluates health probes.

This repository begins with a local `kind` cluster to keep evaluation reproducible and inexpensive. The AWS Terraform root is a non-deployed reference that preserves the same Helm/GitOps delivery contract; live EKS and reusable cross-environment modules remain future work.

## Design decisions

- **Helm over duplicated YAML:** supports environment-specific values while preserving one deployment contract.
- **GitOps pull model:** the cluster reconciles from Git rather than granting the CI runner broad cluster credentials.
- **Dependency-free service on a Distroless runtime:** reduces the package and supply-chain surface. The nonroot tag is pinned to an official immutable image-index digest containing linux/amd64, preventing upstream tag movement from changing the base.
- **Local-first workflow:** lets reviewers reproduce the system without cloud access or cost.

## Release trust boundaries

Pull-request CI is read-only and cannot publish packages, request GitHub OIDC, create attestations, or sign images. Only a semantic-version tag triggers the release job, whose package, identity-token, and attestation writes are job-scoped. The image is built once, scanned and inventoried before publication, then addressed by digest for provenance, SBOM attestation, signing, and verification. No `latest` tag is produced.

The runner, GitHub OIDC and attestation services, GHCR, and Sigstore are external trust boundaries. Argo CD receives no registry-write authority. Future promotion is a reviewed Git change to a verified digest; release CI does not write GitOps state. No release has been published and no GHCR package exists yet. Provenance, SBOM attestation, signing, and verification remain unvalidated. The guard permits bootstrap only for authenticated canonical `NAME_UNKNOWN` after successful token acquisition; uncertainty fails closed. The first release still requires separate authorization. See [release status](supply-chain-security.md#release-status).

## AWS infrastructure blueprint

The non-deployed Terraform root defines a two-AZ VPC with public subnets for NAT and future controlled ingress, plus private EKS worker subnets. The EKS API is private by default; public access requires explicit restricted CIDRs. Managed nodes receive no public IP or SSH configuration. Their launch template enforces encrypted `gp3` root volumes and IMDSv2 with a hop limit suitable for containerized workloads. A configurable NAT strategy trades development cost against availability, while `none` intentionally requires future VPC endpoints.

EKS uses separate control-plane and node IAM roles with only required AWS-managed policy attachments, a restricted additional security group, all control-plane log types with retention, and a rotating KMS key for Kubernetes secrets. Bootstrap administrator access is disabled; an optional reviewed principal can be added through EKS access entries. GitHub and local Argo CD receive no AWS permissions.

CI performs formatting, backend-disabled initialization, validation, TFLint, and Trivy misconfiguration scanning without credentials, plan, or apply. Remote S3/DynamoDB state controls and future Argo CD connectivity are documented but not instantiated. See [../infra/terraform/aws/README.md](../infra/terraform/aws/README.md).

## Argo CD trust boundaries

The Argo CD manifests target `https://github.com/kelechiP/secure-gitops-platform-portfolio.git` over HTTPS. The sanitized portfolio repository is public and anonymously readable over HTTPS; no repository credential is required. No live reconciliation has been validated from this repository. GitHub receives no cluster credential, CI receives no kubeconfig, and the Argo CD server remains a ClusterIP service without public ingress.

The `secure-platform-local` AppProject is Argo CD's logical authorization boundary for this workload. It admits only the repository HTTPS URL, the in-cluster API destination in `secure-platform`, and the five namespaced resource kinds rendered by the local chart. The namespace is created during bootstrap, so the AppProject admits no cluster-scoped kinds. The Application renders `helm/platform-api` and uses automated pruning and self-healing.

This AppProject policy does not reduce the Kubernetes permissions of the locally installed Argo CD application controller. The standard local installation retains broader cluster RBAC, so namespace isolation is not enforced by Kubernetes RBAC in this milestone. A production design should install or configure Argo CD with separately tested least-privilege Kubernetes roles. See [argocd-validation.md](argocd-validation.md) for installation provenance and future reconciliation checks.

## Local observability

The monitoring configuration places Prometheus Operator, Prometheus, Grafana, kube-state-metrics, and node-exporter in the dedicated `monitoring` namespace. A ServiceMonitor selects only the `platform-api-local` Service endpoints and scrapes `/metrics`. Prometheus also collects Kubernetes state and container telemetry used by the provisioned Grafana dashboard. A PrometheusRule evaluates Platform API target availability.

The cluster-wide monitoring stack is a pinned Helm bootstrap because its CRDs, ClusterRoles, and cross-namespace discovery permissions are intentionally separate from application delivery. The `observability-local` Argo CD project manages only ServiceMonitor and PrometheusRule in `secure-platform`; it does not broaden `secure-platform-local`.

Neither AppProject provides Kubernetes RBAC isolation for its controller. Prometheus and its operator also retain broader read/discovery access across the local cluster. See [observability.md](observability.md) for the full data flow, permissions, and validation evidence.
