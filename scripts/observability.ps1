param(
    [ValidateSet("Install", "Remove")]
    [string]$Action = "Install",
    [string]$KubeContext = "kind-secure-gitops",
    [string]$ChartVersion = "88.5.3",
    [string]$TargetRevision = "main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$valuesPath = Join-Path $repoRoot "observability\kube-prometheus-stack-values.yaml"
$dashboardPath = Join-Path $repoRoot "observability\dashboards\platform-api.json"
$projectPath = Join-Path $repoRoot "gitops\clusters\local\observability-project.yaml"
$applicationPath = Join-Path $repoRoot "gitops\clusters\local\observability-application.yaml"
$helmPath = Join-Path $repoRoot ".tools\bin\helm.exe"
if (-not (Test-Path -LiteralPath $helmPath)) {
    $helmPath = "helm"
}

function Invoke-Kubectl {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & kubectl --context $KubeContext @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl failed: $($Arguments -join ' ')"
    }
}

if ($Action -eq "Remove") {
    Invoke-Kubectl --namespace argocd delete application platform-api-observability-local --ignore-not-found=true --wait=true
    Invoke-Kubectl --namespace argocd delete appproject observability-local --ignore-not-found=true
    Invoke-Kubectl --namespace secure-platform delete servicemonitor platform-api --ignore-not-found=true
    Invoke-Kubectl --namespace secure-platform delete prometheusrule platform-api --ignore-not-found=true
    & $helmPath uninstall local-monitoring --kube-context $KubeContext --namespace monitoring --ignore-not-found
    if ($LASTEXITCODE -ne 0) {
        throw "Helm uninstall failed"
    }
    Invoke-Kubectl delete namespace monitoring --ignore-not-found=true
    Invoke-Kubectl label namespace secure-platform observability.secure-platform/enabled-
    Write-Output "Local observability resources removed."
    exit 0
}

Invoke-Kubectl cluster-info | Out-Null

foreach ($namespace in @("monitoring", "secure-platform")) {
    $namespaceYaml = & kubectl --context $KubeContext create namespace $namespace --dry-run=client -o yaml
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to render namespace $namespace"
    }
    $namespaceYaml | & kubectl --context $KubeContext apply -f -
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to apply namespace $namespace"
    }
    Invoke-Kubectl label namespace $namespace observability.secure-platform/enabled=true --overwrite
}

$secretExists = & kubectl --context $KubeContext --namespace monitoring get secret local-grafana-admin --ignore-not-found -o name
if (-not $secretExists) {
    $passwordBytes = New-Object byte[] 24
    [Security.Cryptography.RandomNumberGenerator]::Fill($passwordBytes)
    $password = [Convert]::ToBase64String($passwordBytes)
    $secret = @{
        apiVersion = "v1"
        kind = "Secret"
        metadata = @{
            name = "local-grafana-admin"
            namespace = "monitoring"
        }
        type = "Opaque"
        stringData = @{
            "admin-user" = "admin"
            "admin-password" = $password
        }
    } | ConvertTo-Json -Depth 5
    $secret | & kubectl --context $KubeContext apply -f -
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create the local Grafana credential Secret"
    }
    $password = $null
    $passwordBytes = $null
}

& $helmPath repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
if ($LASTEXITCODE -ne 0) {
    throw "Failed to configure the Prometheus Community Helm repository"
}
& $helmPath repo update prometheus-community
if ($LASTEXITCODE -ne 0) {
    throw "Failed to update the Prometheus Community Helm repository"
}
& $helmPath upgrade --install local-monitoring prometheus-community/kube-prometheus-stack --version $ChartVersion --kube-context $KubeContext --namespace monitoring --values $valuesPath --wait --timeout 10m
if ($LASTEXITCODE -ne 0) {
    throw "Monitoring stack installation failed"
}

foreach ($crd in @("servicemonitors.monitoring.coreos.com", "prometheusrules.monitoring.coreos.com")) {
    Invoke-Kubectl wait --for=condition=Established "crd/$crd" --timeout=120s
}

$dashboardYaml = & kubectl --context $KubeContext --namespace monitoring create configmap platform-api-dashboard --from-file=platform-api.json=$dashboardPath --dry-run=client -o yaml
if ($LASTEXITCODE -ne 0) {
    throw "Failed to render the Grafana dashboard ConfigMap"
}
$dashboardYaml | & kubectl --context $KubeContext apply -f -
if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply the Grafana dashboard ConfigMap"
}
Invoke-Kubectl --namespace monitoring label configmap platform-api-dashboard grafana_dashboard=1 --overwrite

Invoke-Kubectl apply -f $projectPath
if ($TargetRevision -eq "main") {
    Invoke-Kubectl apply -f $applicationPath
} else {
    $applicationJson = & kubectl --context $KubeContext create --dry-run=client -f $applicationPath -o json
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to render the observability Application"
    }
    $application = $applicationJson | ConvertFrom-Json
    $application.spec.source.targetRevision = $TargetRevision
    $application | ConvertTo-Json -Depth 20 | & kubectl --context $KubeContext apply -f -
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to apply the observability Application"
    }
}
Invoke-Kubectl --namespace argocd annotate application platform-api-observability-local argocd.argoproj.io/refresh=hard --overwrite
Invoke-Kubectl --namespace argocd wait application/platform-api-observability-local --for=jsonpath='{.status.sync.status}'=Synced --timeout=300s
Invoke-Kubectl --namespace argocd wait application/platform-api-observability-local --for=jsonpath='{.status.health.status}'=Healthy --timeout=300s

Invoke-Kubectl --namespace monitoring rollout status deployment/local-monitoring-grafana --timeout=300s
Invoke-Kubectl --namespace monitoring rollout status deployment/local-monitoring-kube-prom-operator --timeout=300s
Invoke-Kubectl --namespace monitoring rollout status deployment/local-monitoring-kube-state-metrics --timeout=300s
Invoke-Kubectl --namespace monitoring rollout status daemonset/local-monitoring-prometheus-node-exporter --timeout=300s
Invoke-Kubectl --namespace monitoring rollout status statefulset/prometheus-local-monitoring-kube-prometheus-prometheus --timeout=300s

Write-Output "Local observability installation is ready. See docs/observability.md for verification and port-forward commands."
