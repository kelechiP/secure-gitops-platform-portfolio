# Roadmap

Checked items describe implemented source and static validation. Live deployment and release validation are separate work.

## Foundation

- [x] Dependency-free health and metrics API
- [x] Non-root, digest-pinned Distroless image
- [x] Helm chart with secure pod defaults
- [x] HTTPS Argo CD manifests and local bootstrap helpers
- [x] CI tests, template validation, secret detection, and image scanning
- [ ] Authorized local kind deployment and endpoint checks
- [ ] HTTPS GitOps reconciliation, self-healing, and rollback validation
- [ ] HPA behavior with Metrics Server
- [ ] NetworkPolicy enforcement with a compatible CNI

## Cloud infrastructure

- [x] Non-deployed AWS VPC/EKS Terraform blueprint with static security validation
- [ ] Remote-state bootstrap and deployment identity
- [ ] Authorized EKS reference environment
- [ ] Cost estimate, budget alerts, and tested teardown

## Observability and SRE

- [x] Prometheus/Grafana configuration, dashboard, and target-down alert rule
- [ ] Authorized local deployment and alert validation
- [ ] Availability and latency SLOs
- [ ] Production routing and incident runbooks
- [ ] Load testing and capacity results

## Supply chain and delivery

- [x] Immutable GitHub Action pins and CI enforcement
- [x] SPDX generation and validation in CI
- [x] Version guard, concurrency protection, and seven-day artifact retention
- [x] Release workflow configuration for provenance, SBOM attestation, and signing
- [ ] Separately reviewed first-package bootstrap; absent packages currently fail closed
- [ ] Independently authorized first release and successful provenance, SBOM attestation, signing, and verification
- [ ] Admission policies and external secrets
- [ ] Canary delivery and recovery exercises
