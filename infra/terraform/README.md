# Infraestructura reproducible de Cloud Run

Este módulo adopta y administra el entorno privado de QA existente:

- APIs de Cloud Run, Cloud Build, Artifact Registry, Secret Manager y Storage.
- Registro Docker privado `polar-assistant`.
- Cuenta de ejecución `polar-sport-runtime`, sin claves administradas por el
  usuario.
- Servicio Cloud Run privado, con una instancia máxima, concurrencia uno,
  1 CPU, 512 MiB y una imagen por digest.

No administra la vinculación de facturación, secretos Gemini, buckets de FIT ni
objetos biométricos. Esas operaciones tienen autorización y ciclo de vida
separados. Tampoco publica una política `allUsers` o
`allAuthenticatedUsers`; `service_invokers` queda vacío por defecto.

## Estado remoto

Antes del módulo principal, crear el bucket de estado con el módulo `bootstrap`:

```powershell
Set-Location infra/terraform/bootstrap
terraform init -backend=false
terraform apply -var project_id=polar-verity-robertmx23-2026 `
  -var state_bucket_name=polar-verity-robertmx23-2026-tfstate
Copy-Item ./backend.hcl.example ./backend.hcl
terraform init -migrate-state -backend-config=backend.hcl
```

El bucket usa acceso uniforme, prevención de acceso público y versionado. Los
archivos de estado y `backend.hcl` se ignoran por Git.

## Adopción segura del entorno existente

No ejecutar `apply` en el módulo principal sin importar primero los recursos ya
creados. Desde `infra/terraform`, copiar los ejemplos y ejecutar el script:

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
Copy-Item backend.hcl.example backend.hcl
..\scripts\adopt-existing.ps1
terraform plan
```

El resultado esperado después de revisar el plan es cero recursos para crear o
destruir. El primer `apply` puede actualizar etiquetas y habilitar
`deletion_protection` del servicio; revisarlo antes de aprobarlo.

Para publicar una revisión nueva, construir y verificar localmente la imagen,
publicarla en Artifact Registry y cambiar `container_image` por su digest. Un
`terraform plan` debe mostrar sólo la revisión esperada.
