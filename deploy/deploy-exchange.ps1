<#
.SYNOPSIS
    Grant Exchange Online permissions for the Logic App connector identity.
.DESCRIPTION
    The Logic App needs FullAccess to the shared mailbox so the Office 365
    Outlook connector can read incoming emails and save attachments.
    After running this script, the Logic App connector must be authorized
    with a one-time OAuth sign-in in the Azure Portal.
.NOTES
    Requires the ExchangeOnlineManagement PowerShell module:
      Install-Module ExchangeOnlineManagement -Scope CurrentUser
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

$sharedMailbox = $configJson.mailbox.target_shared_mailbox
$connectorUPN  = $configJson.mailbox.logic_app_connector_identity_upn

if (-not $sharedMailbox -or -not $connectorUPN) {
    Write-Host "ERROR: mailbox.target_shared_mailbox and mailbox.logic_app_connector_identity_upn must be set in config." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Exchange Online Permissions ===" -ForegroundColor Cyan
Write-Host "Shared Mailbox : $sharedMailbox"
Write-Host "Connector UPN  : $connectorUPN`n"

Import-Module ExchangeOnlineManagement -ErrorAction Stop
Connect-ExchangeOnline -ShowBanner:$false

# Grant FullAccess (read emails, list attachments)
Write-Host "[1/2] Granting FullAccess on $sharedMailbox..." -ForegroundColor Yellow
Add-MailboxPermission `
    -Identity $sharedMailbox `
    -User $connectorUPN `
    -AccessRights FullAccess `
    -InheritanceType All `
    -AutoMapping $false `
    -ErrorAction SilentlyContinue

# Grant SendAs (optional, for reply/notification Logic Apps)
Write-Host "[2/2] Granting SendAs on $sharedMailbox..." -ForegroundColor Yellow
Add-RecipientPermission `
    -Identity $sharedMailbox `
    -Trustee $connectorUPN `
    -AccessRights SendAs `
    -Confirm:$false `
    -ErrorAction SilentlyContinue

Disconnect-ExchangeOnline -Confirm:$false

Write-Host "`n=== Exchange permissions granted ===" -ForegroundColor Green
Write-Host "NEXT STEP: In the Azure Portal, open the Logic App and authorize" -ForegroundColor Yellow
Write-Host "           the Office 365 Outlook connector with a one-time sign-in" -ForegroundColor Yellow
Write-Host "           using the account: $connectorUPN" -ForegroundColor Yellow
