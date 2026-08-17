# Go-live smoke checks (PowerShell)
# Uso: .\scripts\go-live-smoke.ps1 -BackendUrl https://api.4seo.app -FrontendUrl https://4seo.app

param(
  [Parameter(Mandatory = $true)][string]$BackendUrl,
  [string]$FrontendUrl = "https://4seo.app"
)

$ErrorActionPreference = "Stop"
$BackendUrl = $BackendUrl.TrimEnd("/")
$FrontendUrl = $FrontendUrl.TrimEnd("/")
$failed = 0

function Test-Url([string]$Url, [string]$Name, [int[]]$Ok = @(200)) {
  try {
    $resp = Invoke-WebRequest -Uri $Url -Method GET -MaximumRedirection 5 -UseBasicParsing -TimeoutSec 30
    if ($Ok -contains [int]$resp.StatusCode) {
      Write-Host "OK  $Name ($($resp.StatusCode)) $Url"
    } else {
      Write-Host "FAIL $Name ($($resp.StatusCode)) $Url"
      $script:failed++
    }
  } catch {
    Write-Host "FAIL $Name — $($_.Exception.Message) — $Url"
    $script:failed++
  }
}

Write-Host "=== Smoke go-live ==="
Test-Url "$BackendUrl/api/health" "backend health"
Test-Url "$BackendUrl/api/info" "backend info"
Test-Url "$FrontendUrl/" "frontend home"
Test-Url "$FrontendUrl/login" "frontend login"
Test-Url "$FrontendUrl/checkout/" "frontend checkout"

Write-Host ""
if ($failed -gt 0) {
  Write-Host "RESULT: $failed falha(s)"
  exit 1
}
Write-Host "RESULT: todos os checks basicos passaram"
exit 0
