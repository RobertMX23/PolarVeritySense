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
