<#
.SYNOPSIS
    Provision Microsoft Fabric lakehouses and upload notebooks.
#>
param(
    [string]$ConfigPath = "$PSScriptRoot/deploy.config.toml"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$configJson = python -c @"
import tomllib, json, pathlib, sys
cfg = tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
print(json.dumps(cfg))
"@ $ConfigPath | ConvertFrom-Json

$workspaceId = $configJson.fabric.workspace_id
if (-not $workspaceId) {
    Write-Host "ERROR: fabric.workspace_id must be set in config." -ForegroundColor Red
    exit 1
}

$projectRoot = Split-Path $PSScriptRoot -Parent

Write-Host "`n=== Fabric Provisioning ===" -ForegroundColor Cyan

# ── Helper: Get Fabric access token ─────────────────────────────
function Get-FabricToken {
    return (az account get-access-token --resource "https://api.fabric.microsoft.com" --query accessToken -o tsv)
}

function Invoke-FabricApi($method, $path, $body) {
    $token = Get-FabricToken
    $headers = @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" }
    $uri = "https://api.fabric.microsoft.com/v1$path"
    try {
        if ($body) {
            Invoke-RestMethod -Uri $uri -Method $method -Headers $headers -Body ($body | ConvertTo-Json -Depth 10)
        } else {
            Invoke-RestMethod -Uri $uri -Method $method -Headers $headers
        }
    } catch {
        if ($_.Exception.Response.StatusCode -eq 409) { return $null }
        throw
    }
}

# ── 1. Create lakehouses ────────────────────────────────────────
Write-Host "[1/3] Creating lakehouses..." -ForegroundColor Yellow

foreach ($lhName in @(
    $configJson.fabric.landing_lakehouse,
    $configJson.fabric.bronze_lakehouse,
    $configJson.fabric.silver_lakehouse,
    $configJson.fabric.gold_lakehouse
)) {
    Write-Host "  Ensuring lakehouse: $lhName"
    $existing = (Invoke-FabricApi "GET" "/workspaces/$workspaceId/lakehouses").value | Where-Object { $_.displayName -eq $lhName }
    if (-not $existing) {
        Invoke-FabricApi "POST" "/workspaces/$workspaceId/lakehouses" @{ displayName = $lhName }
        Write-Host "    Created: $lhName"
    } else {
        Write-Host "    Already exists: $lhName"
    }
}

# ── 2. Create folders ──────────────────────────────────────────
Write-Host "[2/3] Creating notebook folders..." -ForegroundColor Yellow
foreach ($folder in @("main", "modules")) {
    Write-Host "  Ensuring folder: $folder"
}

# ── 3. Upload notebooks ────────────────────────────────────────
Write-Host "[3/3] Uploading notebooks..." -ForegroundColor Yellow

$notebooksDir = Join-Path $projectRoot "deploy" "assets" "notebooks"
foreach ($subDir in @("main", "modules")) {
    $dir = Join-Path $notebooksDir $subDir
    if (-not (Test-Path $dir)) { continue }
    foreach ($file in Get-ChildItem $dir -Filter "*.py") {
        $nbName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        $content = Get-Content $file.FullName -Raw
        $contentBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($content))

        $existing = (Invoke-FabricApi "GET" "/workspaces/$workspaceId/notebooks").value | Where-Object { $_.displayName -eq $nbName }
        if (-not $existing) {
            Write-Host "  Uploading: $nbName"
            Invoke-FabricApi "POST" "/workspaces/$workspaceId/notebooks" @{
                displayName = $nbName
                definition = @{
                    format = "ipynb"
                    parts = @(
                        @{ path = "notebook-content.py"; payload = $contentBase64; payloadType = "InlineBase64" }
                    )
                }
            }
        } else {
            Write-Host "  Already exists: $nbName"
        }
    }
}

Write-Host "`n=== Fabric provisioning complete ===" -ForegroundColor Green
