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

variable "sync_service_account_id" {
  description = "Short ID for the dedicated identity that synchronizes curated Polar sessions."
  type        = string
  default     = "polar-sport-sync"
}

variable "firestore_database_id" {
  description = "Firestore database ID used for curated operational session records."
  type        = string
  default     = "(default)"
}

variable "firestore_location" {
  description = "Regional Firestore location for curated sessions. This location cannot be changed after database creation."
  type        = string
  default     = "us-central1"
}

variable "firestore_qa_subject_id" {
  description = "Non-personal technical Firestore subject exposed only after IAP session binding in the private QA service."
  type        = string
  default     = "ath_local_smoke_2026"

  validation {
    condition     = can(regex("^ath_[A-Za-z0-9_-]{8,128}$", var.firestore_qa_subject_id))
    error_message = "firestore_qa_subject_id must be an opaque ath_ identifier."
  }
}

variable "container_image" {
  description = "Immutable Artifact Registry image digest. Do not use a mutable tag."
  type        = string
}

variable "gemini_model" {
  description = "Stable Vertex AI Gemini model used by the bounded inference gateway."
  type        = string
  default     = "gemini-3.8-flash"

  validation {
    condition     = length(trimspace(var.gemini_model)) > 0
    error_message = "gemini_model must name a Vertex AI model."
  }
}

variable "gemini_location" {
  description = "Vertex AI location for the selected Gemini model; this can differ from the Cloud Run region."
  type        = string
  default     = "global"

  validation {
    condition     = length(trimspace(var.gemini_location)) > 0
    error_message = "gemini_location must be a Vertex AI location."
  }
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
