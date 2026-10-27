variable "project_id" {
  type        = string
  description = "Existing project that will own the Terraform state bucket."
}

variable "location" {
  type        = string
  description = "Bucket location."
  default     = "US"
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique bucket name for Terraform state."
}

provider "google" {
  project = var.project_id
}

resource "google_storage_bucket" "terraform_state" {
  name                        = var.state_bucket_name
  project                     = var.project_id
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  labels = {
    purpose     = "terraform-state"
    managed-by  = "terraform"
    environment = "qa"
  }
}
