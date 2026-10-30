[CmdletBinding()]
param(
    [string]$ProjectId = "polar-verity-robertmx23-2026",
    [string]$Region = "us-central1",
    [string]$RepositoryId = "polar-assistant",
    [string]$ServiceAccountId = "polar-sport-runtime",
    [string]$ServiceName = "polar-sport-assistant"
)

$ErrorActionPreference = "Stop"
$moduleRoot = Join-Path (Split-Path -Parent $PSScriptRoot) "terraform"
Set-Location $moduleRoot

$terraformCommand = Get-Command terraform -ErrorAction SilentlyContinue
$terraformExe = if ($terraformCommand) {
    $terraformCommand.Source
}
else {
    Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Hashicorp.Terraform_Microsoft.Winget.Source_8wekyb3d8bbwe\terraform.exe"
}

if (-not (Test-Path $terraformExe)) {
    throw "Terraform is not installed or not available on PATH. Install HashiCorp Terraform before adoption."
}

function Invoke-Terraform {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $terraformExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Terraform failed: terraform $($Arguments -join ' ')"
    }
}

if (-not (Test-Path "backend.hcl")) {
    throw "Missing backend.hcl. Copy backend.hcl.example, bootstrap the state bucket, and initialize the backend first."
}

$previousInitArgs = $env:TF_CLI_ARGS_init
$env:TF_CLI_ARGS_init = "-backend-config=backend.hcl"
try {
    Invoke-Terraform init
}
finally {
    if ($null -eq $previousInitArgs) {
        Remove-Item Env:TF_CLI_ARGS_init -ErrorAction SilentlyContinue
    }
    else {
        $env:TF_CLI_ARGS_init = $previousInitArgs
    }
}

$imports = @(
    @{ Address = 'google_project_service.required["artifactregistry.googleapis.com"]'; Id = "$ProjectId/artifactregistry.googleapis.com" },
    @{ Address = 'google_project_service.required["cloudbuild.googleapis.com"]'; Id = "$ProjectId/cloudbuild.googleapis.com" },
    @{ Address = 'google_project_service.required["run.googleapis.com"]'; Id = "$ProjectId/run.googleapis.com" },
    @{ Address = 'google_project_service.required["secretmanager.googleapis.com"]'; Id = "$ProjectId/secretmanager.googleapis.com" },
    @{ Address = 'google_project_service.required["storage.googleapis.com"]'; Id = "$ProjectId/storage.googleapis.com" },
    @{ Address = 'google_artifact_registry_repository.images'; Id = "projects/$ProjectId/locations/$Region/repositories/$RepositoryId" },
    @{ Address = 'google_service_account.runtime'; Id = "projects/$ProjectId/serviceAccounts/$ServiceAccountId@$ProjectId.iam.gserviceaccount.com" },
    @{ Address = 'google_cloud_run_v2_service.qa'; Id = "projects/$ProjectId/locations/$Region/services/$ServiceName" }
)

foreach ($item in $imports) {
    $state = & $terraformExe state show $item.Address 2>$null
    if ($LASTEXITCODE -eq 0 -and $state) {
        Write-Host "Already managed: $($item.Address)"
        continue
    }
    Invoke-Terraform import $item.Address $item.Id
}

Write-Host "Adoption complete. Review terraform plan; do not apply an unexpected change."
