terraform {
  required_version = ">= 1.16.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Configure after bootstrap with: terraform init -backend-config=backend.hcl
  backend "gcs" {}
}
