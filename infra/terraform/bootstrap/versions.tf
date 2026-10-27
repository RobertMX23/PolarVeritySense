terraform {
  required_version = ">= 1.16.0"

  # First initialization uses -backend=false. After the bucket exists, run
  # init -migrate-state with bootstrap/backend.hcl to move this state to GCS.
  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}
