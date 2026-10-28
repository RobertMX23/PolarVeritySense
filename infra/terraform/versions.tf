terraform {
  required_version = ">= 1.16.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      # Direct IAP support for google_cloud_run_v2_service (iap_enabled) is
      # available in the current 7.x provider line.
      version = "~> 7.0"
    }
  }

  # Configure after bootstrap with: terraform init -backend-config=backend.hcl
  backend "gcs" {}
}
