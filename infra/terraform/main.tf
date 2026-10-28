locals {
  required_apis = toset([
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudbuild.googleapis.com",
    "iap.googleapis.com",
    "logging.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each           = local.required_apis
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_repository_id
  description   = "Private container images for PolarVeritySense Cloud Run QA"
  format        = "DOCKER"

  depends_on = [google_project_service.required["artifactregistry.googleapis.com"]]
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = var.runtime_service_account_id
  display_name = "Polar Sport Assistant Cloud Run runtime"
  description  = "Dedicated runtime identity for the private PolarVeritySense QA service; no user-managed keys."
}

# The workload identity is the only principal that can invoke Gemini through
# Vertex AI. No user-managed Gemini API key is created, stored or mounted.
resource "google_project_iam_member" "runtime_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.runtime.email}"

  depends_on = [google_project_service.required["aiplatform.googleapis.com"]]
}

resource "google_cloud_run_v2_service" "qa" {
  name                = var.service_name
  location            = var.region
  project             = var.project_id
  ingress             = "INGRESS_TRAFFIC_ALL"
  iap_enabled         = var.enable_iap
  deletion_protection = true

  labels = {
    environment = "qa"
    component   = "sport-assistant"
    managed-by  = "terraform"
  }

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 1
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"

    labels = {
      environment = "qa"
      component   = "sport-assistant"
      managed-by  = "terraform"
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = var.container_image

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }

      # Current ADK name for Google Cloud Agent Platform mode. The gateway also
      # sets Vertex mode explicitly, keeping this compatible with ADK upgrades.
      env {
        name  = "GOOGLE_GENAI_USE_ENTERPRISE"
        value = "TRUE"
      }

      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }

      env {
        name  = "VERTEX_GEMINI_LOCATION"
        value = var.gemini_location
      }

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        startup_cpu_boost = true
        cpu_idle          = true
      }
    }
  }

  depends_on = [
    google_project_service.required["run.googleapis.com"],
    google_artifact_registry_repository.images,
    google_project_iam_member.runtime_vertex_user,
  ]

  lifecycle {
    prevent_destroy = true

    # Cloud Run returns a service-level manual-scaling value of zero which the
    # provider does not expose as a configurable argument. Ignore that
    # representation; the template scaling block above remains documented and
    # the postcondition keeps the effective cap at one instance.
    ignore_changes = [
      scaling,
    ]

    postcondition {
      condition     = self.template[0].scaling[0].max_instance_count == 1
      error_message = "Cloud Run must remain capped at one instance for this QA environment."
    }
  }
}

# IAP is the only identity permitted to invoke the service once IAP is enabled.
# It is a Google-managed service agent, not a user-managed credential.
resource "google_cloud_run_v2_service_iam_member" "iap_invoker" {
  count = var.enable_iap ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.qa.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-iap.iam.gserviceaccount.com"

  depends_on = [google_project_service.required["iap.googleapis.com"]]
}

# Keep the list authoritative at this service only. A blank list deliberately
# creates no policy: IAP can be enabled before a human access list is approved.
resource "google_iap_web_cloud_run_service_iam_binding" "authorized_users" {
  count = var.enable_iap && length(var.iap_access_members) > 0 ? 1 : 0

  project                = var.project_id
  location               = var.region
  cloud_run_service_name = google_cloud_run_v2_service.qa.name
  role                   = "roles/iap.httpsResourceAccessor"
  members                = var.iap_access_members

  depends_on = [google_project_service.required["iap.googleapis.com"]]
}

resource "google_cloud_run_v2_service_iam_member" "invokers" {
  for_each = var.service_invokers

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.qa.name
  role     = "roles/run.invoker"
  member   = each.value
}
