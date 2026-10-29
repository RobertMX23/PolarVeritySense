# Infraestructura reproducible de Cloud Run

Este módulo adopta y administra el entorno privado de QA existente:

- APIs de Cloud Run, Cloud Build, Cloud Logging, Artifact Registry, Secret Manager,
  Storage, Vertex AI y Firestore.
- Registro Docker privado `polar-assistant`.
- Cuenta de ejecución `polar-sport-runtime`, sin claves administradas por el
  usuario. Sólo recibe `roles/aiplatform.user` para usar Gemini por Vertex AI.
- Servicio Cloud Run privado, con una instancia máxima, concurrencia uno,
  1 CPU, 512 MiB y una imagen por digest.
- IAP directo opcional. Al habilitarlo, la URL `run.app` muestra el inicio de
  sesión de Google antes de llegar al contenedor; no crea un balanceador, IP,
  dominio ni una política pública.
- Base Firestore Native regional en `us-central1` para sesiones curadas. El
  runtime sólo recibe `roles/datastore.viewer`; `polar-sport-sync` recibe
  `roles/datastore.user` para escribir resúmenes validados. Ninguna identidad
  recibe claves administradas por usuarios.

No administra la vinculación de facturación, claves Gemini, buckets de FIT ni
objetos biométricos crudos. La inferencia usa credenciales predeterminadas de la
cuenta de ejecución y no requiere un secreto. Los FIT conservan su autorización
y ciclo de vida separados. Tampoco publica una política `allUsers` o
`allAuthenticatedUsers`; `service_invokers` queda vacío por defecto.

## Acceso web con Google SSO

Para este servicio único se usa IAP **directo** sobre Cloud Run. Es la
arquitectura recomendada por Google para proteger también la URL `run.app` y
evitar un balanceador adicional. El módulo habilita la API IAP, activa
`iap_enabled`, concede `roles/run.invoker` únicamente al agente administrado
de IAP y aplica una lista explícita de `iap_access_members` con el rol
`roles/iap.httpsResourceAccessor`.

Antes del primer `apply` con `enable_iap = true`, configurar en Google Auth
Platform un cliente OAuth externo si se permitirán cuentas Gmail o cuentas
fuera de una organización de Google Workspace. Google exige ese paso inicial
en consola para proyectos sin organización; el secreto del cliente no se
guarda en Terraform, Git ni el estado. Después, usar una lista concreta de
usuarios `user:...` o un grupo `group:...` en `iap_access_members`.

No usar `allUsers`, `allAuthenticatedUsers` ni un dominio completo salvo una
decisión de acceso explícita. Mantener `service_invokers = []`: el único
invocador de Cloud Run debe ser el agente de IAP.

La arquitectura, el procedimiento de alta inicial y la señal de diagnóstico
del cliente OAuth faltante están en
[IAP_DIRECT_ARCHITECTURE.md](IAP_DIRECT_ARCHITECTURE.md).

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
