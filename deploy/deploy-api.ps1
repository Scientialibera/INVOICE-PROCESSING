<#
.SYNOPSIS
    Build frontend, deploy API + SPA to App Service, seed assistant prompt.
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

$prefix        = $configJson.naming.prefix
$rgName        = if ($configJson.azure.resource_group_name) { $configJson.azure.resource_group_name } else { "rg-$prefix" }
function Coalesce($val, $default) { if ($val) { $val } else { $default } }
$apiAppName    = Coalesce $configJson.naming.app_service_name "api-$prefix"
$storageAccount = Coalesce $configJson.naming.storage_account_name "st$($prefix -replace '[^a-z0-9]','')"

$projectRoot = Split-Path $PSScriptRoot -Parent

Write-Host "`n=== Deploy API + Frontend ===" -ForegroundColor Cyan

# ── 1. Build frontend ──────────────────────────────────────────
Write-Host "[1/4] Building frontend..." -ForegroundColor Yellow
$frontendDir = Join-Path $projectRoot "frontend"
if (Test-Path (Join-Path $frontendDir "package.json")) {
    Push-Location $frontendDir
    npm ci
    npm run build
    Pop-Location

    $distDir  = Join-Path $frontendDir "dist"
    $staticDir = Join-Path $projectRoot "api" "static"
    if (Test-Path $staticDir) { Remove-Item -Recurse -Force $staticDir }
    Copy-Item -Recurse $distDir $staticDir
    Write-Host "  Frontend build copied to api/static/"
} else {
    Write-Host "  SKIP: No frontend/package.json found" -ForegroundColor DarkGray
}

# ── 2. ZIP deploy API ──────────────────────────────────────────
Write-Host "[2/4] ZIP-deploying API to App Service..." -ForegroundColor Yellow
$apiDir = Join-Path $projectRoot "api"
$zipPath = Join-Path $env:TEMP "api-deploy.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }

Push-Location $apiDir
Compress-Archive -Path "./*" -DestinationPath $zipPath -Force
Pop-Location

az webapp deploy `
    --name $apiAppName `
    --resource-group $rgName `
    --src-path $zipPath `
    --type zip `
    --output none

Remove-Item $zipPath -ErrorAction SilentlyContinue

# ── 3. Seed assistant prompt ────────────────────────────────────
Write-Host "[3/4] Seeding assistant system prompt..." -ForegroundColor Yellow
$promptsContainer = $configJson.storage.prompts_container_name

$promptSource = Join-Path $projectRoot $configJson.paths.assistant_prompt_source
if (Test-Path $promptSource) {
    az storage blob upload `
        --account-name $storageAccount `
        --container-name $promptsContainer `
        --name $configJson.prompts.assistant_system_prompt `
        --file $promptSource `
        --auth-mode login `
        --overwrite `
        --output none
    Write-Host "  Uploaded $($configJson.prompts.assistant_system_prompt)"
}

# ── 4. Verify ───────────────────────────────────────────────────
Write-Host "[4/4] Verifying deployment..." -ForegroundColor Yellow
$url = az webapp show --name $apiAppName --resource-group $rgName --query "defaultHostName" -o tsv
Write-Host "  API available at: https://$url"

Write-Host "`n=== API deployment complete ===" -ForegroundColor Green
