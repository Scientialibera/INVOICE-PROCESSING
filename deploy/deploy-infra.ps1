<#
.SYNOPSIS
    Idempotent Azure infrastructure provisioning for Spend Analyzer.
.DESCRIPTION
    Provisions all Azure resources using Azure CLI. Every resource is
    created only if it does not already exist. Names derive from
    deploy.config.toml [naming].prefix when left empty.
#>
param(
    [string]$ConfigPath = "$PSScriptRoot/deploy.config.toml"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Load TOML via Python ────────────────────────────────────────
$configJson = python -c @"
import tomllib, json, pathlib, sys
cfg = tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
print(json.dumps(cfg))
"@ $ConfigPath | ConvertFrom-Json

$prefix   = $configJson.naming.prefix
$location = $configJson.azure.location
$rgName   = if ($configJson.azure.resource_group_name) { $configJson.azure.resource_group_name } else { "rg-$prefix" }

function Coalesce($val, $default) { if ($val) { $val } else { $default } }

$storageAccountName  = Coalesce $configJson.naming.storage_account_name   "st$($prefix -replace '[^a-z0-9]','')"
$functionAppName     = Coalesce $configJson.naming.function_app_name      "func-$prefix"
$apiAppName          = Coalesce $configJson.naming.app_service_name       "api-$prefix"
$sbNamespace         = Coalesce $configJson.naming.servicebus_namespace_name "sbns-$prefix"
$openaiAccountName   = Coalesce $configJson.naming.openai_account_name    "aoai-$prefix"
$docintelAccountName = Coalesce $configJson.naming.docintel_account_name  "doci-$prefix"
$cosmosAccountName   = Coalesce $configJson.naming.cosmos_account_name    "cosmos-$prefix"
$searchServiceName   = Coalesce $configJson.naming.search_service_name    "search-$prefix"

$processQueue         = $configJson.queues.process_queue_name
$cosmosDb             = $configJson.cosmos.database_name
$cosmosInvoices       = $configJson.cosmos.invoices_container_name
$cosmosInvoicesPk     = $configJson.cosmos.invoices_partition_key
$cosmosSessions       = $configJson.cosmos.sessions_container_name
$cosmosSessionsPk     = $configJson.cosmos.sessions_partition_key

Write-Host "`n=== Spend Analyzer Infrastructure ===" -ForegroundColor Cyan
Write-Host "Resource Group : $rgName"
Write-Host "Location       : $location"
Write-Host "Prefix         : $prefix`n"

# ── 1. Resource Group ───────────────────────────────────────────
Write-Host "[1/12] Resource Group..." -ForegroundColor Yellow
az group create --name $rgName --location $location --output none

# ── 2. Storage Account + Containers ─────────────────────────────
Write-Host "[2/12] Storage Account..." -ForegroundColor Yellow
az storage account create `
    --name $storageAccountName `
    --resource-group $rgName `
    --location $location `
    --sku Standard_LRS `
    --kind StorageV2 `
    --min-tls-version TLS1_2 `
    --allow-blob-public-access false `
    --output none 2>$null

foreach ($container in @(
    $configJson.storage.uploads_container_name,
    $configJson.storage.prompts_container_name,
    $configJson.storage.function_definitions_container_name,
    $configJson.storage.schemas_container_name
)) {
    az storage container create `
        --account-name $storageAccountName `
        --name $container `
        --auth-mode login `
        --output none 2>$null
}

# ── 3. Service Bus + Queue ──────────────────────────────────────
Write-Host "[3/12] Service Bus..." -ForegroundColor Yellow
az servicebus namespace create `
    --name $sbNamespace `
    --resource-group $rgName `
    --location $location `
    --sku Standard `
    --output none 2>$null

az servicebus queue create `
    --namespace-name $sbNamespace `
    --resource-group $rgName `
    --name $processQueue `
    --enable-session false `
    --output none 2>$null

# ── 4. Cosmos DB ────────────────────────────────────────────────
Write-Host "[4/12] Cosmos DB..." -ForegroundColor Yellow
az cosmosdb create `
    --name $cosmosAccountName `
    --resource-group $rgName `
    --locations regionName=$location `
    --capabilities EnableServerless `
    --default-consistency-level Session `
    --output none 2>$null

az cosmosdb sql database create `
    --account-name $cosmosAccountName `
    --resource-group $rgName `
    --name $cosmosDb `
    --output none 2>$null

az cosmosdb sql container create `
    --account-name $cosmosAccountName `
    --resource-group $rgName `
    --database-name $cosmosDb `
    --name $cosmosInvoices `
    --partition-key-path $cosmosInvoicesPk `
    --output none 2>$null

az cosmosdb sql container create `
    --account-name $cosmosAccountName `
    --resource-group $rgName `
    --database-name $cosmosDb `
    --name $cosmosSessions `
    --partition-key-path $cosmosSessionsPk `
    --output none 2>$null

# ── 5. Azure OpenAI ─────────────────────────────────────────────
if ($configJson.openai.deploy_openai_resources -eq $true) {
    Write-Host "[5/12] Azure OpenAI..." -ForegroundColor Yellow
    az cognitiveservices account create `
        --name $openaiAccountName `
        --resource-group $rgName `
        --location $location `
        --kind OpenAI `
        --sku S0 `
        --custom-domain $openaiAccountName `
        --output none 2>$null

    az cognitiveservices account deployment create `
        --name $openaiAccountName `
        --resource-group $rgName `
        --deployment-name $configJson.openai.deployment_name `
        --model-name $configJson.openai.model_name `
        --model-version $configJson.openai.model_version `
        --model-format OpenAI `
        --sku-name $configJson.openai.deployment_sku_name `
        --sku-capacity $configJson.openai.capacity `
        --output none 2>$null

    az cognitiveservices account deployment create `
        --name $openaiAccountName `
        --resource-group $rgName `
        --deployment-name $configJson.openai.embedding_deployment_name `
        --model-name $configJson.openai.embedding_model_name `
        --model-version $configJson.openai.embedding_model_version `
        --model-format OpenAI `
        --sku-name $configJson.openai.embedding_sku_name `
        --sku-capacity $configJson.openai.embedding_capacity `
        --output none 2>$null
} else {
    Write-Host "[5/12] Azure OpenAI -- SKIPPED (deploy_openai_resources=false)" -ForegroundColor DarkGray
}

# ── 6. Document Intelligence ────────────────────────────────────
if ($configJson.docintel.deploy_docintel_resources -eq $true) {
    Write-Host "[6/12] Document Intelligence..." -ForegroundColor Yellow
    az cognitiveservices account create `
        --name $docintelAccountName `
        --resource-group $rgName `
        --location $location `
        --kind FormRecognizer `
        --sku $configJson.docintel.sku_name `
        --custom-domain $docintelAccountName `
        --output none 2>$null
} else {
    Write-Host "[6/12] Document Intelligence -- SKIPPED" -ForegroundColor DarkGray
}

# ── 7. AI Search ────────────────────────────────────────────────
Write-Host "[7/12] AI Search..." -ForegroundColor Yellow
az search service create `
    --name $searchServiceName `
    --resource-group $rgName `
    --location $location `
    --sku $configJson.search.sku `
    --output none 2>$null

# ── 8. Function App (Flex Consumption) ──────────────────────────
Write-Host "[8/12] Function App..." -ForegroundColor Yellow
$funcExists = az functionapp show --name $functionAppName --resource-group $rgName --query "name" -o tsv 2>$null
if (-not $funcExists) {
    az functionapp create `
        --name $functionAppName `
        --resource-group $rgName `
        --storage-account $storageAccountName `
        --flexconsumption-location $location `
        --runtime python `
        --runtime-version 3.13 `
        --functions-version 4 `
        --output none
}
az functionapp identity assign --name $functionAppName --resource-group $rgName --output none 2>$null

# ── 9. App Service (API + SPA) ──────────────────────────────────
Write-Host "[9/12] App Service..." -ForegroundColor Yellow
$planName = "plan-$prefix"
az appservice plan create `
    --name $planName `
    --resource-group $rgName `
    --location $location `
    --sku $configJson.app_service.plan_sku `
    --is-linux `
    --output none 2>$null

$apiExists = az webapp show --name $apiAppName --resource-group $rgName --query "name" -o tsv 2>$null
if (-not $apiExists) {
    az webapp create `
        --name $apiAppName `
        --resource-group $rgName `
        --plan $planName `
        --runtime $configJson.app_service.runtime `
        --output none
}
az webapp identity assign --name $apiAppName --resource-group $rgName --output none 2>$null
az webapp config set --name $apiAppName --resource-group $rgName --always-on true --startup-file "gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app" --output none 2>$null

# ── 10. RBAC ────────────────────────────────────────────────────
Write-Host "[10/12] RBAC assignments..." -ForegroundColor Yellow

$funcMI = az functionapp identity show --name $functionAppName --resource-group $rgName --query principalId -o tsv
$apiMI  = az webapp identity show --name $apiAppName --resource-group $rgName --query principalId -o tsv
$rgId   = az group show --name $rgName --query id -o tsv

$storageId   = az storage account show --name $storageAccountName --resource-group $rgName --query id -o tsv
$sbId        = az servicebus namespace show --name $sbNamespace --resource-group $rgName --query id -o tsv
$openaiId    = az cognitiveservices account show --name $openaiAccountName --resource-group $rgName --query id -o tsv 2>$null
$docintelId  = az cognitiveservices account show --name $docintelAccountName --resource-group $rgName --query id -o tsv 2>$null
$cosmosId    = az cosmosdb show --name $cosmosAccountName --resource-group $rgName --query id -o tsv
$searchId    = az search service show --name $searchServiceName --resource-group $rgName --query id -o tsv

function Ensure-Role($principalId, $roleDefinition, $scope) {
    if (-not $principalId -or -not $scope) { return }
    $existing = az role assignment list --assignee $principalId --role $roleDefinition --scope $scope --query "[0].id" -o tsv 2>$null
    if (-not $existing) {
        az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --role $roleDefinition --scope $scope --output none 2>$null
    }
}

foreach ($mi in @($funcMI, $apiMI)) {
    Ensure-Role $mi "Storage Blob Data Contributor"       $storageId
    Ensure-Role $mi "Cognitive Services OpenAI User"      $openaiId
    Ensure-Role $mi "Search Index Data Reader"            $searchId
}

Ensure-Role $funcMI "Azure Service Bus Data Receiver"     $sbId
Ensure-Role $funcMI "Cognitive Services User"             $docintelId
Ensure-Role $apiMI  "Azure Service Bus Data Sender"       $sbId

# Cosmos SQL data-plane role
$cosmosAccountId = $cosmosId
foreach ($mi in @($funcMI, $apiMI)) {
    if (-not $mi) { continue }
    $existing = az cosmosdb sql role assignment list --account-name $cosmosAccountName --resource-group $rgName --query "[?principalId=='$mi'] | [0].id" -o tsv 2>$null
    if (-not $existing) {
        az cosmosdb sql role assignment create `
            --account-name $cosmosAccountName `
            --resource-group $rgName `
            --role-definition-id "00000000-0000-0000-0000-000000000002" `
            --principal-id $mi `
            --scope "/" `
            --output none 2>$null
    }
}

# ── 11. Function App Settings ───────────────────────────────────
Write-Host "[11/12] Function App settings..." -ForegroundColor Yellow
$openaiEndpoint  = "https://$openaiAccountName.openai.azure.com/"
$docintelEndpoint = "https://$docintelAccountName.cognitiveservices.azure.com/"
$searchEndpoint  = "https://$searchServiceName.search.windows.net"
$cosmosEndpoint  = az cosmosdb show --name $cosmosAccountName --resource-group $rgName --query documentEndpoint -o tsv
$sbFqdn          = "$sbNamespace.servicebus.windows.net"

az functionapp config appsettings set --name $functionAppName --resource-group $rgName --output none --settings `
    "STORAGE_ACCOUNT_NAME=$storageAccountName" `
    "UPLOADS_CONTAINER_NAME=$($configJson.storage.uploads_container_name)" `
    "PROMPTS_CONTAINER_NAME=$($configJson.storage.prompts_container_name)" `
    "FUNCTION_DEFINITIONS_CONTAINER_NAME=$($configJson.storage.function_definitions_container_name)" `
    "SERVICEBUS_CONNECTION__fullyQualifiedNamespace=$sbFqdn" `
    "SERVICEBUS_QUEUE_NAME=$processQueue" `
    "COSMOS_ENDPOINT=$cosmosEndpoint" `
    "COSMOS_DATABASE_NAME=$cosmosDb" `
    "COSMOS_INVOICES_CONTAINER=$cosmosInvoices" `
    "AOAI_ENDPOINT=$openaiEndpoint" `
    "AOAI_DEPLOYMENT=$($configJson.openai.deployment_name)" `
    "AOAI_DEPLOYMENT_EMBEDDING=$($configJson.openai.embedding_deployment_name)" `
    "AOAI_API_VERSION=$($configJson.openai.api_version)" `
    "DOCINTEL_ENDPOINT=$docintelEndpoint" `
    "SEARCH_ENDPOINT=$searchEndpoint" `
    "SEARCH_INDEX=$($configJson.search.index_name)" `
    "SEARCH_USE_EMBEDDINGS=$($configJson.search.use_embeddings)" `
    "ACTIVE_MODEL_PROFILE=$($configJson.app_settings.active_model_profile)" `
    "CLASSIFICATION_PROMPT_BLOB_NAME=$($configJson.prompts.classification_prompt)" `
    "CLASSIFICATION_FUNC_DEF_BLOB_NAME=$($configJson.function_definitions.classification_func_def)" `
    "CONFIDENCE_THRESHOLD=$($configJson.app_settings.confidence_threshold_required)"

# ── 12. App Service Settings ────────────────────────────────────
Write-Host "[12/12] App Service settings..." -ForegroundColor Yellow
az webapp config appsettings set --name $apiAppName --resource-group $rgName --output none --settings `
    "STORAGE_ACCOUNT_NAME=$storageAccountName" `
    "UPLOADS_CONTAINER_NAME=$($configJson.storage.uploads_container_name)" `
    "PROMPTS_CONTAINER_NAME=$($configJson.storage.prompts_container_name)" `
    "COSMOS_ENDPOINT=$cosmosEndpoint" `
    "COSMOS_DATABASE_NAME=$cosmosDb" `
    "COSMOS_INVOICES_CONTAINER=$cosmosInvoices" `
    "COSMOS_SESSIONS_CONTAINER=$cosmosSessions" `
    "AZURE_OPENAI_ENDPOINT=$openaiEndpoint" `
    "AZURE_OPENAI_DEPLOYMENT=$($configJson.openai.deployment_name)" `
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$($configJson.openai.embedding_deployment_name)" `
    "AZURE_OPENAI_API_VERSION=$($configJson.openai.api_version)" `
    "SEARCH_ENDPOINT=$searchEndpoint" `
    "SEARCH_INDEX=$($configJson.search.index_name)" `
    "AGENT_NAME=$($configJson.agent.name)" `
    "AGENT_SYSTEM_PROMPT_BLOB=$($configJson.agent.system_prompt_blob)" `
    "AGENT_ENABLE_CODE_INTERPRETER=$($configJson.agent.enable_code_interpreter)" `
    "ENTRA_TENANT_ID=$($configJson.entra.tenant_id)" `
    "ENTRA_API_CLIENT_ID=$($configJson.entra.api_client_id)" `
    "SCM_DO_BUILD_DURING_DEPLOYMENT=true"

Write-Host "`n=== Infrastructure provisioning complete ===" -ForegroundColor Green
