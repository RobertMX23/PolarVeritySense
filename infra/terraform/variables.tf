variable "project_id" {
  description = "Existing Google Cloud project that hosts the private QA service."
  type        = string
}

variable "region" {
  description = "Cloud Run and Artifact Registry region."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Private Cloud Run service name."
  type        = string
  default     = "polar-sport-assistant"
}

variable "artifact_repository_id" {
  description = "Artifact Registry Docker repository ID."
  type        = string
  default     = "polar-assistant"
}

variable "runtime_service_account_id" {
  description = "Short ID for the dedicated Cloud Run runtime identity."
  type        = string
  default     = "polar-sport-runtime"
}

variable "container_image" {
  description = "Immutable Artifact Registry image digest. Do not use a mutable tag."
  type        = string
}

variable "service_invokers" {
  description = "IAM principals allowed to invoke the private service, such as user:name@example.com. Empty keeps access at inherited project IAM only."
  type        = set(string)
  default     = []
}

variable "enable_iap" {
  description = "Enable direct Identity-Aware Proxy on Cloud Run. This protects the run.app URL with Google sign-in and keeps the service non-public."
  type        = bool
  default     = false
}

variable "iap_access_members" {
  description = "Google principals allowed through IAP, for example user:person@gmail.com or group:team@googlegroups.com. Do not use allUsers or allAuthenticatedUsers."
  type        = set(string)
  default     = []
}
