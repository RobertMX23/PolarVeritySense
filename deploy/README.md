# Cloud Run: entorno privado de QA

Destino desplegado: proyecto `polar-verity-robertmx23-2026`, región
`us-central1`, servicio `polar-sport-assistant`. El código fuente público está
en https://github.com/RobertMX23/PolarVeritySense; el servicio sigue protegido
por IAM y no se convierte en público por la visibilidad del repositorio.

La siguiente configuración de acceso web usa IAP directo: Google muestra el
inicio de sesión y sólo entrega la petición a Cloud Run cuando la cuenta está
en la política IAP. El cambio está declarado en
[`infra/terraform`](../infra/terraform/README.md); no requiere balanceador ni
un dominio propio para proteger la URL `run.app`.

IAP está habilitado y el cliente OAuth externo vive sólo en Google Auth
Platform; una petición anónima a la URL devuelve `302` hacia Google Sign-In.
La aplicación OAuth está en modo de pruebas: la cuenta propietaria figura como
usuaria de prueba y miembro de IAP. Para añadir otra cuenta Gmail, añadirla
tanto a los usuarios de prueba OAuth como a `iap_access_members`, y aplicar
Terraform. El secreto OAuth no se guarda en el repositorio, el estado ni
archivos de proyecto. El procedimiento se mantiene en
[`IAP_DIRECT_ARCHITECTURE.md`](../infra/terraform/IAP_DIRECT_ARCHITECTURE.md).

La facturación está vinculada y los servicios Cloud Run, Cloud Build, Artifact
Registry, Secret Manager y Vertex AI están habilitados. La revisión
`polar-sport-assistant-00003-rr5` recibe 100% del tráfico desde la imagen
inmutable `sha256:f364a476385450d6e280a52430b2b89e97e926ea295473dfaa4bb9b8e7b156dc`.
La imagen inicia ADK 2.12.0 con Python 3.13.18 y el mismo
`SportAssistantRoot`.

La comprobación IAM contra el servicio devolvió HTTP 200 para `/version`,
`/list-apps` y el grafo de la aplicación. No ejecutó Gemini, no incluyó una
clave ni montó FIT. Es una prueba de disponibilidad y de autenticación, no una
prueba integrada de recomendaciones.

## Configuración vigente

| Recurso | Configuración |
|---|---|
| Cloud Run | Servicio privado; autenticación IAM obligatoria |
| Capacidad | 1 CPU, 512 MiB, mínimo 0, máximo 1 instancia, concurrencia 1 |
| Peticiones | Puerto 8080; timeout 300 segundos |
| Imagen | Linux amd64; usuario sin privilegios; mismo `root_agent` |
| Modelos | Vertex AI: `gemini-3.8-flash` mediante endpoint `global`; máximo 3 generaciones por caso |
| Artefactos | Artifact Registry privado: `polar-assistant` |
| Credencial Gemini | Application Default Credentials de `polar-sport-runtime`; sin API key ni secreto montado |
| Modo ADK | `GOOGLE_GENAI_USE_ENTERPRISE=TRUE`, compatible con Google Cloud Agent Platform |
| FIT | No se copió ninguno. Si no existe un montaje autorizado, usa dos sesiones sintéticas no personales etiquetadas como demo; un bucket privado y montaje de sólo lectura siguen requiriendo autorización. |
| Sesiones | SQLite en `/tmp/polar-adk`; efímeras en esta prueba |
| Auditoría | Simulación; exportar la evidencia antes de que termine la instancia |

Los archivos FIT, `.env`, reportes, bases SQLite y el historial Git no forman
parte del contexto de construcción. `.dockerignore` y `.gcloudignore` usan una
lista explícita de archivos permitidos.

## Demo cloud sin FIT

La imagen no contiene FIT ni intenta descargarlos. En ausencia de
`POLAR_FIT_DIR`, el flujo demo crea dos sesiones sintéticas con métricas
deterministas y marca el estado como `synthetic_cloud_demo`. Sirve para validar
ADK, IAP y el recorrido de propuesta sin atribuir resultados a una persona. Un
montaje de FIT aprobado conserva la ruta de evidencia local original; AccessLink
requiere su configuración y autorización separadas.

## Operación como código

La infraestructura se administra desde [infra/terraform](../infra/terraform/README.md).
Incluye el bootstrap del backend GCS, la adopción de los recursos existentes y
la configuración declarativa del servicio. Ejecutar `terraform plan` antes de
cualquier cambio; el estado, `backend.hcl` y los valores por entorno permanecen
fuera de Git.

## Comprobación local sin secretos ni FIT

```powershell
docker build --platform linux/amd64 -f deploy/Dockerfile -t polar-verity-sense:qa .
docker run --rm -p 127.0.0.1:8088:8080 --env PORT=8080 polar-verity-sense:qa
```

En otra terminal, consultar `http://127.0.0.1:8088/version` y
`http://127.0.0.1:8088/list-apps`. El contenedor por sí solo no puede analizar
los FIT reales: `POLAR_FIT_DIR` apunta al montaje externo. El directorio local
original sigue siendo el valor por defecto cuando no se define esa variable.

Las seis dependencias directas se fijan en `requirements.txt`; las transitivas
y la etiqueta de la imagen base pueden cambiar en una futura reconstrucción.
Se debe conservar el digest de la imagen efectivamente desplegada.

## Inferencia integrada sin claves personales

La revisión de QA invoca Vertex AI con la identidad de carga de Cloud Run. El
módulo Terraform habilita `aiplatform.googleapis.com`, concede sólo
`roles/aiplatform.user` a `polar-sport-runtime` y fija el proyecto, región y
modelo de forma explícita. No existe una clave de Gemini en Secret Manager,
variables de entorno ni imagen.

La demo cloud sigue usando sesiones sintéticas y no personales. Si se autoriza
una prueba con FIT reales, copiar únicamente los archivos autorizados a un
bucket privado y conceder al runtime lectura de esos objetos. No incorporarlos
a la imagen ni reutilizar la aprobación de un caso anterior.

Cloud Run permanece en `us-central1`. El modelo se invoca desde la ubicación
Vertex `global`, que es la ubicación publicada para `gemini-3.8-flash`;
esa diferencia se declara con `VERTEX_GEMINI_LOCATION` y no cambia la región
del servicio ni del almacenamiento.

## Referencia de despliegue reproducible

Para una nueva imagen, ejecutar Cloud Build con `deploy/cloudbuild.yaml` y
desplegar el digest con `--no-allow-unauthenticated`, cuenta dedicada,
`--min=0 --max=1 --max-instances=1 --concurrency=1 --cpu=1 --memory=512Mi
--timeout=300`. Incorporar el secreto y montaje únicamente si se autorizaron.
Acceder autenticadamente, por ejemplo mediante un token de identidad temporal;
no hacer público ADK Web para facilitar la prueba.


## Medición y límites de la prueba

Medir cada petición con reloj monotónico del cliente, y registrar además UTC
para correlacionar con la revisión y los logs. Separar arranque observado,
preparación, analista, crítico, espera humana y auditoría. El total continuo
incluye la espera humana. No atribuir al servidor el tiempo de navegación ni
inferir un intervalo estadístico a partir de una sola ejecución. Exportar una
tabla con inicio, fin, duración, fuente del reloj y limitaciones.

SQLite, memoria y artefactos locales se pierden al reemplazar la instancia.
Máximo una instancia y concurrencia uno no convierten el bloqueo local en una
garantía distribuida ni proporcionan continuidad entre revisiones. El entorno
sirve para QA; no demuestra persistencia de producción. El límite de instancias
tampoco es un límite monetario: compilación, almacenamiento y modelos pueden
generar cargos por separado.

Referencias oficiales: [contrato del contenedor](https://docs.cloud.google.com/run/docs/container-contract),
[despliegue ADK](https://adk.dev/deploy/cloud-run/),
[máximo de instancias](https://docs.cloud.google.com/run/docs/configuring/max-instances).
