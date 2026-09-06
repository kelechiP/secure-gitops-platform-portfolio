# Repository Guidance

## Layout

- `app/`: dependency-free Python HTTP service, tests, and Dockerfile.
- `helm/platform-api/`: Helm chart for the service and operational resources.
- `gitops/clusters/local/`: Argo CD Application for the local reconciliation workflow.
- `docs/`: architecture, security model, roadmap, and validation notes.
- `kind-config.yaml`: local two-node kind cluster definition.
- `scripts/`: local workflow helpers, including the pinned Argo CD installer.

## Commands

- Tests: `python -m unittest discover -s app/tests -v`
- Syntax: `python -m compileall -q app/src app/tests`
- Image: `docker build -t secure-gitops-platform-portfolio:local ./app`
- Helm: `helm lint helm/platform-api` and `helm template platform-api helm/platform-api --namespace secure-platform`
- Cluster: `kind create cluster --name secure-gitops --config kind-config.yaml`
- Load: `kind load docker-image secure-gitops-platform-portfolio:local --name secure-gitops`
- Deploy: `helm upgrade --install platform-api ./helm/platform-api --kube-context kind-secure-gitops --namespace secure-platform --create-namespace --set image.repository=secure-gitops-platform-portfolio --set image.tag=local --set image.pullPolicy=IfNotPresent`
- Verify: `kubectl --context kind-secure-gitops -n secure-platform rollout status deployment/platform-api --timeout=120s`
- Argo CD: `.\scripts\install-argocd.ps1` and `kubectl --context kind-secure-gitops apply -f gitops/clusters/local/application.yaml`

## Engineering constraints

- Preserve non-root execution, a read-only root filesystem, disabled privilege escalation, dropped capabilities, RuntimeDefault seccomp, explicit resources, a dedicated service account, disabled token mounting, and NetworkPolicy resources.
- Never commit credentials, kubeconfig, local tools, virtual environments, caches, generated secrets, Terraform state, or build artifacts.
- Never print or commit secret values. Repository authentication and live GitOps validation are deferred while this repository remains private.
- Keep Trivy HIGH/CRITICAL and Gitleaks gates enabled. Fix findings rather than weakening gates.
- Pin supply-chain inputs by immutable digest or commit SHA when practical; document remaining tag-based references.
- Do not imply that planned cloud, GitOps, observability, scaling, signing, or policy features have been deployed or validated.
- Do not add automated-tool attribution or related branding to repository content, branches, commits, releases, or pull requests.

## Git and verification

- Branch from `main` with focused names such as `feat/<scope>` or `fix/<scope>`; never force-push or rewrite shared history.
- Use concise imperative commit messages and keep unrelated user changes untouched.
- Before committing, review `git status`, `git diff --check`, and the complete proposed diff.
- Run tests, compilation, Helm lint/render, the container security scan, and relevant local cluster checks for affected changes.
- Report checks as passed, failed, blocked, skipped, or not tested. A manifest existing is not proof that its controller or enforcement behavior works.
