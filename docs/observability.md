# Local observability

This local monitoring configuration is intended for a disposable kind-secure-gitops cluster. It has not been deployed from this repository; the steps below describe a future authorized validation exercise.

## Architecture and decision

The local stack uses Prometheus Community kube-prometheus-stack because it supplies Prometheus Operator CRDs, Prometheus, Grafana, kube-state-metrics, and node-exporter as one reproducible package.

    Platform API /metrics
            |
    ServiceMonitor in secure-platform
            |
    Prometheus Operator -> Prometheus in monitoring
            |                    |
    PrometheusRule               +-> Grafana data source
                                         |
                                  provisioned dashboard

The monitoring stack is installed by Helm rather than Argo CD. The stack owns cluster-scoped CRDs, ClusterRoles, and discovery permissions that do not belong in the existing application AppProject. Project-specific ServiceMonitor and PrometheusRule objects remain GitOps-managed through the separate observability-local AppProject, which allows only those two namespaced kinds in secure-platform. The existing secure-platform-local AppProject is unchanged.

AppProject restrictions are logical Argo CD policy. They do not reduce the broader Kubernetes RBAC installed for Prometheus Operator, Prometheus, or the local Argo CD controller.

## Pinned versions

The bootstrap pins kube-prometheus-stack chart 88.5.3, with these configured core component versions:

- Prometheus 3.14.0
- Prometheus Operator 0.93.1
- Grafana 13.2.0
- kube-state-metrics 2.20.0
- node-exporter 1.12.1
- Grafana dashboard sidecar 2.10.1

The chart is pinned by version, not by package digest. Container images use explicit version tags but are not pinned by digest.

## Prerequisites and installation order

Prerequisites are Docker Desktop, the existing kind-secure-gitops cluster, kubectl, Helm 3, Argo CD, the Platform API image loaded into kind, and anonymous HTTPS access to the public portfolio repository. No repository credential is required. GitOps installation and live monitoring, HPA behavior, and NetworkPolicy enforcement remain unvalidated and require separate authorization.

The script performs this order:

1. Create and label monitoring and label secure-platform for explicit Prometheus discovery.
2. Generate a random Grafana password and store it only in the local local-grafana-admin Secret.
3. Install the pinned monitoring chart and wait for the required CRDs.
4. Create the dashboard ConfigMap from the version-controlled JSON.
5. Apply observability-local before platform-api-observability-local.
6. Wait for Argo CD and every monitoring workload to become healthy.

Run from PowerShell:

    .\scripts\observability.ps1

## Verification

Check workloads and GitOps applications:

    kubectl --context kind-secure-gitops --namespace monitoring get pods
    kubectl --context kind-secure-gitops --namespace secure-platform get servicemonitor,prometheusrule
    kubectl --context kind-secure-gitops --namespace argocd get application platform-api-local platform-api-observability-local

Forward Prometheus locally; no ingress or LoadBalancer is created:

    kubectl --context kind-secure-gitops --namespace monitoring port-forward service/local-monitoring-kube-prom-prometheus 9090:9090

Open http://127.0.0.1:9090/targets and verify both Platform API targets are Up. Useful queries are:

    platform_http_requests_total
    platform_uptime_seconds
    sum(kube_pod_status_ready{namespace="secure-platform",pod=~"platform-api-.*",condition="true"})
    sum(kube_pod_container_status_restarts_total{namespace="secure-platform",pod=~"platform-api-.*",container="api"})
    sum(rate(container_cpu_usage_seconds_total{namespace="secure-platform",pod=~"platform-api-.*",container="api"}[5m]))
    sum(container_memory_working_set_bytes{namespace="secure-platform",pod=~"platform-api-.*",container="api"})

## Grafana

Grafana is a ClusterIP service. Forward it locally:

    kubectl --context kind-secure-gitops --namespace monitoring port-forward service/local-monitoring-grafana 3000:80

The user is admin. Retrieve the generated local password only when needed:

    $encoded = kubectl --context kind-secure-gitops --namespace monitoring get secret local-grafana-admin -o jsonpath='{.data.admin-password}'
    [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded))

Do not paste the password into documentation, logs, commits, issues, or pull requests. Open http://127.0.0.1:3000 and select **Secure Platform API - Local Observability**. The provisioned dashboard contains request rate, application uptime, Ready pod count, restart count, CPU, and memory panels. Prometheus is provisioned automatically as data source UID prometheus.

## Alert validation

PlatformApiTargetDown becomes warning severity after any discovered Platform API target reports `up == 0` for two minutes, or when no matching Platform API `up` series exists for two minutes. Its description directs the operator to the Deployment, Service, Endpoints, and NetworkPolicy.

For a safe local test, temporarily change only the ServiceMonitor path, observe Pending then Firing under http://127.0.0.1:9090/alerts, and immediately restore the committed manifest:

    kubectl --context kind-secure-gitops --namespace secure-platform patch servicemonitor platform-api --type=json -p '[{"op":"replace","path":"/spec/endpoints/0/path","value":"/alert-validation-unavailable"}]'

    helm template platform-api-observability .\helm\platform-api --namespace secure-platform --set monitoring.resourcesOnly=true --set monitoring.enabled=true | kubectl --context kind-secure-gitops --namespace secure-platform apply -f -

Argo CD self-healing also restores the ServiceMonitor when the observability Application manages it.

## Resource and storage profile

Prometheus requests 200 millicores and 512 MiB, with limits of one CPU and 1 GiB. Grafana requests 50 millicores and 128 MiB, with limits of 250 millicores and 256 MiB. Operator, kube-state-metrics, and node-exporter have smaller explicit bounds in the values file.

Prometheus retention is 24 hours with a 1 GB limit. Storage is ephemeral emptyDir; data disappears with the pod or cluster and is not suitable for long-term analysis.

## Cleanup

Remove only observability resources:

    .\scripts\observability.ps1 -Action Remove

This removes the observability Application/AppProject, the two Platform API monitoring CRs, the Helm release, the generated Grafana Secret, and the monitoring namespace. It does not delete secure-platform, the Platform API, Argo CD or the kind cluster.

## Validation scope

Helm templates, the pinned monitoring chart, and the dashboard JSON can be validated without a cluster. Live discovery, Grafana provisioning, alert firing/recovery, endpoint access, and Argo CD health remain unvalidated from this repository and require a separately authorized local deployment.

## Known limitations

- This is a single-cluster, single-replica, local-only monitoring stack.
- Alertmanager and external notification receivers are disabled; no email, Slack, PagerDuty, or production escalation exists.
- Storage is ephemeral, retention is short, and there is no remote write or long-term archive.
- Grafana and Prometheus are accessed only by local port-forwarding.
- The chart installs broad cluster discovery RBAC and cluster-scoped CRDs. This is acceptable only for the disposable local environment.
- kind's default CNI does not enforce the Platform API NetworkPolicy.
- There are no SLOs, recording rules, high availability, backup, or capacity guarantees yet.
