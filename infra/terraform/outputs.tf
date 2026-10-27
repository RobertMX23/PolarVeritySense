output "project_number" {
  value = data.google_project.current.number
}

output "artifact_repository" {
  value = google_artifact_registry_repository.images.name
}

output "runtime_service_account" {
  value = google_service_account.runtime.email
}

output "service_uri" {
  value = google_cloud_run_v2_service.qa.uri
}
