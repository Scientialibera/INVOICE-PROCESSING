<#
.SYNOPSIS
    Publish Azure Functions, seed blobs, sync triggers, create Event Grid subscription.
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

$prefix          = $configJson.naming.prefix
$rgName          = if ($configJson.azure.resource_group_name) { $configJson.azure.resource_group_name } else { "rg-$prefix" }
function Coalesce($val, $default) { if ($val) { $val } else { $default } }
$functionAppName = Coalesce $configJson.naming.function_app_name "func-$prefix"
$storageAccount  = Coalesce $configJson.naming.storage_account_name "st$($prefix -replace '[^a-z0-9]','')"

Write-Host "`n=== Deploy Azure Functions ===" -ForegroundColor Cyan

# ── 1. Publish ──────────────────────────────────────────────────
Write-Host "[1/4] Publishing function app..." -ForegroundColor Yellow
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
func azure functionapp publish $functionAppName --python
Pop-Location

# ── 2. Seed blobs ──────────────────────────────────────────────
Write-Host "[2/4] Seeding prompts and function definitions..." -ForegroundColor Yellow

function Upload-BlobFromFile($containerName, $blobName, $localPath) {
    $fullPath = Join-Path (Split-Path $PSScriptRoot -Parent) $localPath
    if (-not (Test-Path $fullPath)) {
        Write-Host "  SKIP: $fullPath not found" -ForegroundColor DarkGray
        return
    }
    Write-Host "  $containerName/$blobName <- $localPath"
    az storage blob upload `
        --account-name $storageAccount `
        --container-name $containerName `
        --name $blobName `
        --file $fullPath `
        --auth-mode login `
        --overwrite `
        --output none
}

$promptsContainer  = $configJson.storage.prompts_container_name
$funcDefsContainer = $configJson.storage.function_definitions_container_name

Upload-BlobFromFile $promptsContainer  $configJson.prompts.classification_prompt       $configJson.paths.classification_prompt_source
Upload-BlobFromFile $funcDefsContainer $configJson.function_definitions.classification_func_def $configJson.paths.classification_func_def_source

# ── 3. Sync triggers ───────────────────────────────────────────
Write-Host "[3/4] Syncing function triggers..." -ForegroundColor Yellow
$funcId = az functionapp show --name $functionAppName --resource-group $rgName --query id -o tsv
az rest --method post --uri "$funcId/syncfunctiontriggers?api-version=2023-12-01" --output none

Start-Sleep -Seconds 10

# ── 4. Event Grid subscription ──────────────────────────────────
Write-Host "[4/4] Event Grid subscription..." -ForegroundColor Yellow

az provider register --namespace Microsoft.EventGrid --wait 2>$null

$storageId = az storage account show --name $storageAccount --resource-group $rgName --query id -o tsv
$subscriptionName = "evg-invoice-upload-created"

$existingSub = az eventgrid event-subscription show --name $subscriptionName --source-resource-id $storageId --query "name" -o tsv 2>$null
if (-not $existingSub) {
    $retries = 0
    $maxRetries = 6
    while ($retries -lt $maxRetries) {
        $funcUrl = az functionapp function show --name $functionAppName --resource-group $rgName --function-name "InvoiceIntake" --query "invokeUrlTemplate" -o tsv 2>$null
        if ($funcUrl) { break }
        $retries++
        Write-Host "  Waiting for InvoiceIntake function to register ($retries/$maxRetries)..."
        Start-Sleep -Seconds 10
    }

    if (-not $funcUrl) {
        Write-Host "  WARNING: InvoiceIntake function not found. Event Grid subscription skipped." -ForegroundColor Red
    } else {
        $funcKey = az functionapp keys list --name $functionAppName --resource-group $rgName --query "systemKeys.blobs_extension" -o tsv 2>$null
        if (-not $funcKey) {
            $funcKey = az functionapp keys list --name $functionAppName --resource-group $rgName --query "masterKey" -o tsv
        }
        $endpoint = "$funcUrl?code=$funcKey"

        az eventgrid event-subscription create `
            --name $subscriptionName `
            --source-resource-id $storageId `
            --endpoint $endpoint `
            --endpoint-type webhook `
            --included-event-types "Microsoft.Storage.BlobCreated" `
            --subject-begins-with "/blobServices/default/containers/$($configJson.storage.uploads_container_name)/blobs/" `
            --subject-ends-with "" `
            --output none
        Write-Host "  Created Event Grid subscription: $subscriptionName"
    }
} else {
    Write-Host "  Event Grid subscription already exists: $subscriptionName"
}

Write-Host "`n=== Function deployment complete ===" -ForegroundColor Green
