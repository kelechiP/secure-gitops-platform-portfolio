#!/usr/bin/env bash
set -euo pipefail

cluster_name="${CLUSTER_NAME:-secure-gitops}"
image_name="${IMAGE_NAME:-secure-gitops-platform-portfolio:local}"
kube_context="kind-${cluster_name}"

kind create cluster --name "${cluster_name}" --config kind-config.yaml
docker build -t "${image_name}" ./app
kind load docker-image "${image_name}" --name "${cluster_name}"
helm upgrade --install platform-api ./helm/platform-api \
  --kube-context "${kube_context}" \
  --namespace secure-platform --create-namespace \
  --set image.repository=secure-gitops-platform-portfolio \
  --set image.tag=local \
  --set image.pullPolicy=IfNotPresent
kubectl --context "${kube_context}" -n secure-platform \
  rollout status deployment/platform-api --timeout=120s
