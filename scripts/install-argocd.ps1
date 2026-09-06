[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$kubeContext = "kind-secure-gitops"
$namespace = "argocd"
$version = "v3.5.1"
$upstreamCommit = "109ca7ca71139e514114499d294a492e7910a965"
$expectedSha256 = "795a3a972224da6a7f9d32c3e946445f062b60fb46028476715affeb688236e3"
$manifestUrl = "https://raw.githubusercontent.com/argoproj/argo-cd/$upstreamCommit/manifests/install.yaml"
$manifestPath = Join-Path ([IO.Path]::GetTempPath()) "argocd-install-$upstreamCommit.yaml"

try {
    Invoke-WebRequest -UseBasicParsing -Uri $manifestUrl -OutFile $manifestPath
    $actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $expectedSha256) {
        throw "Argo CD manifest checksum mismatch for $version"
    }

    kubectl --context $kubeContext create namespace $namespace `
        --dry-run=client -o yaml |
        kubectl --context $kubeContext apply -f -
    kubectl --context $kubeContext --namespace $namespace apply `
        --server-side --force-conflicts -f $manifestPath

    kubectl --context $kubeContext --namespace $namespace get deployment -o name |
        ForEach-Object {
            kubectl --context $kubeContext --namespace $namespace rollout status $_ --timeout=300s
        }
    kubectl --context $kubeContext --namespace $namespace get statefulset -o name |
        ForEach-Object {
            kubectl --context $kubeContext --namespace $namespace rollout status $_ --timeout=300s
        }
}
finally {
    if (Test-Path -LiteralPath $manifestPath) {
        Remove-Item -LiteralPath $manifestPath -Force
    }
}
