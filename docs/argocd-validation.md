# GitOps configuration and validation guide

The manifests target `https://github.com/kelechiP/secure-gitops-platform-portfolio.git`. The sanitized portfolio repository is public and anonymous HTTPS access is available without repository credentials. Live reconciliation remains unvalidated and requires a separately authorized local exercise. No authentication material or live validation evidence is included.

## Installation provenance

The installer pins Argo CD `v3.5.1` to upstream commit `109ca7ca71139e514114499d294a492e7910a965` and verifies manifest SHA-256 `795a3a972224da6a7f9d32c3e946445f062b60fb46028476715affeb688236e3`. These are upstream supply-chain pins, not project history. Server-side apply supports the large ApplicationSet CRD.

## Trust boundaries

The `secure-platform-local` AppProject allows the portfolio HTTPS URL, the in-cluster `secure-platform` destination, and only ServiceAccount, Service, Deployment, NetworkPolicy, and PodDisruptionBudget. The namespace must be created separately. No cluster-scoped resource kinds are allowed by this project.

The local Application uses `main`, automated pruning, and self-healing. HPA is disabled in its values because the local workflow does not install Metrics Server. It uses `secure-gitops-platform-portfolio:local`, which must be built and loaded into kind before deployment. The monitoring Application has a separate AppProject permitting only ServiceMonitor and PrometheusRule.

AppProjects restrict Argo CD's logical actions; they do not reduce the controller's Kubernetes RBAC. The standard local controller retains broad cluster permissions. GitHub Actions receives no kubeconfig, and the Argo CD server remains ClusterIP-only.

## Future authorized local exercise

After local deployment is separately authorized:

1. Build the portfolio local image and load it into the named kind cluster.
2. Run the pinned installer and create `secure-platform` explicitly.
3. Apply each AppProject before its Application.
4. Require `Synced` and `Healthy`, Ready pods, and HTTP 200 responses from all four API endpoints.
5. Make a controlled replica-count drift and verify self-healing.
6. Review a Git values change, then revert it and verify reconciliation of the new desired state.
7. Record fresh results without credentials, operational identifiers, or local user paths.

These are procedures, not claims that a deployment has occurred. No AWS or Kubernetes resources were deployed during repository initialization.
