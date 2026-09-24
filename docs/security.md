# Security model

## Implemented controls

- Unprivileged runtime user and group
- Read-only root filesystem
- Runtime-default seccomp profile
- No privilege escalation and all capabilities dropped
- No automatic service-account token mount
- CPU and memory limits
- Ingress and egress NetworkPolicy resources
- Secret detection and container vulnerability scanning in CI
- Minimal application dependencies
- Public, anonymous HTTPS GitOps repository access; live reconciliation remains unvalidated
- ClusterIP-only Prometheus and Grafana services
- Generated local Grafana credentials stored only in a Kubernetes Secret
- Separate AppProject allowlist for ServiceMonitor and PrometheusRule
- AppProject allowlists for the local repository, destination namespace, and rendered namespaced resource kinds
- Full-commit pins for every remote GitHub Action, enforced by tested CI validation
- Read-only PR permissions separated from release-only package, OIDC, and attestation writes
- Pre-publication HIGH/CRITICAL scanning and SPDX JSON SBOM generation
- Digest-scoped provenance, SBOM attestation, and keyless signing/verification workflow

## Non-deployed AWS blueprint controls

- Private EKS worker subnets and private-by-default Kubernetes API endpoint
- No worker public IP assignment or SSH remote access configuration
- Explicit encrypted `gp3` managed-node root volumes with deletion on termination
- Required IMDSv2 tokens with metadata hop limit 2 for containerized workloads
- Required EKS IAM roles separated between control plane and nodes
- KMS envelope encryption for Kubernetes secrets with key rotation
- All EKS control-plane log types with bounded retention
- Credential-free Terraform formatting, validation, TFLint, and Trivy CI gates

These controls describe configuration only. No AWS account, runtime IAM policy, endpoint reachability, or enforcement behavior has been tested.

## Trust boundaries

The source repository, GitHub Actions, container registry, Argo CD control plane, and Kubernetes API are separate trust boundaries. Future cloud deployments will use short-lived workload identity and GitHub OIDC rather than static access keys.

No repository authentication material is included. The public portfolio repository supports anonymous HTTPS GitOps access without repository credentials; live reconciliation is currently deferred. The local Argo CD installation script uses a ClusterIP server service.

The `secure-platform-local` AppProject provides logical source, destination, and resource-kind restrictions inside Argo CD. It does not constrain the Kubernetes service-account permissions held by the Argo CD application controller. The standard local controller installation retains broader cluster RBAC; Kubernetes RBAC namespace isolation has not been implemented or tested.

The monitoring Helm release installs cluster-scoped CRDs and broad read/discovery RBAC needed by Prometheus Operator and Prometheus. The separate `observability-local` AppProject limits GitOps-managed monitoring objects but does not reduce those Kubernetes permissions. No monitoring service is publicly exposed, and no dashboard password is stored in Git.

## Limitations

- The local environment is not a production security boundary.
- The current network policy permits application ingress from any namespace to make local evaluation straightforward.
- kind's default CNI does not enforce NetworkPolicy; resource rendering alone does not demonstrate enforcement.
- HPA scaling was not verified because Metrics Server is not installed.
- The [verified `v0.1.0` release](verified-first-release.md) has a public GHCR package and independently verified provenance, SBOM attestation, and keyless signature. These guarantees are digest-specific, not cluster admission enforcement. The release guard allows first-package bootstrap only for authenticated canonical `NAME_UNKNOWN` after successful token acquisition, and otherwise fails closed. Future releases still require separate authorization.
- Signature admission control, external secrets, and policy-as-code remain roadmap items.
- Immutable Action pins require reviewed maintenance to receive upstream fixes.
- The Distroless base is digest-pinned and requires reviewed updates for security fixes. Kubernetes does not enforce signatures at admission.
- AppProject restrictions are enforced by Argo CD, while the local application controller still has broader Kubernetes RBAC.
- Monitoring data and credentials are ephemeral local cluster state, with no backup or long-term retention.
- Alertmanager and external notification routing are not installed.
- The AWS foundation has not been planned or applied, and provider/API behavior is unverified against a real account.
- A single development NAT gateway is a cost/availability tradeoff; no-NAT mode needs future VPC endpoints.
- Remote state, deployment identity, EKS add-ons, workload identity, backups, and admission controls are deferred.
- Supplying `cluster_admin_principal_arn` grants a broad cluster-admin policy and requires separate access governance.

Never commit real credentials, kubeconfig files, Terraform state, customer information, or proprietary infrastructure details.
