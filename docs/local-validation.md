# Local validation scope

Validation covers application and script tests, Python compilation, immutable Action references, workflow YAML and actionlint, Helm lint/rendering, Terraform formatting and backend-disabled validation, TFLint, misconfiguration scanning, Docker build, container vulnerability scanning, SPDX SBOM generation, and secret detection.

These checks do not deploy AWS or Kubernetes resources. The Terraform blueprint is statically validated, not planned or applied. Live endpoint, Argo CD reconciliation, monitoring, HPA, and NetworkPolicy enforcement checks require a separate authorized local exercise.

## Reproduction

```powershell
python -m unittest discover -s app/tests -v
python -m unittest discover -s scripts/tests -v
python -m compileall -q app/src app/tests scripts
python scripts/validate_action_pins.py
actionlint
helm lint helm/platform-api
helm template platform-api helm/platform-api --namespace secure-platform
terraform fmt -check -recursive infra/terraform/aws
terraform -chdir=infra/terraform/aws init -backend=false -input=false
terraform -chdir=infra/terraform/aws validate
tflint --chdir=infra/terraform/aws --init
tflint --chdir=infra/terraform/aws --format compact
trivy config --severity HIGH,CRITICAL --exit-code 1 infra/terraform/aws
docker build -t secure-gitops-platform-portfolio:local ./app
trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 secure-gitops-platform-portfolio:local
gitleaks git --redact --no-banner .
git diff --check
```

CI additionally exercises digest deployment, rejects conflicting tag/digest values and malformed digests, renders monitoring resources and the pinned monitoring stack, and generates an SPDX JSON SBOM with a nonempty package inventory. SBOM generation does not publish an image, create provenance or attestations, or sign anything.

## Limits

- The separately authorized [first container release](verified-first-release.md) passed live bootstrap, publication, and independent attestation/signature verification. Local mocked tests still cover rejected registry states; future releases require separate authorization.
- Actions use full commit pins and the Distroless runtime uses an immutable digest; these inputs require reviewed updates.
- The monitoring chart and its images retain version tags rather than immutable digests.
- HPA needs Metrics Server, and kind's default CNI does not enforce NetworkPolicy.
- Kubernetes admission does not enforce signatures.
