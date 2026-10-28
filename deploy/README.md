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

IAP está habilitado en el servicio. Para cuentas Gmail o cuentas fuera de
Google Workspace falta el alta inicial del cliente OAuth externo en Google Auth
Platform. Mientras esa credencial no exista, la URL devuelve el diagnóstico de
IAP `502 Empty Google Account OAuth client ID(s)/secret(s)`; no es un fallo de
ADK ni una política pública. El procedimiento se mantiene en
[`IAP_DIRECT_ARCHITECTURE.md`](../infra/terraform/IAP_DIRECT_ARCHITECTURE.md).

La facturación está vinculada y los servicios Cloud Run, Cloud Build, Artifact
Registry y Secret Manager están habilitados. La revisión
`polar-sport-assistant-00002-4k5` recibe 100% del tráfico desde la imagen
inmutable `sha256:bd952e4c6c74eb5d8db9e0398d64904deaf526bb2ca9d32e35f51d173054f24d`.
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
| Modelos | Gemini configurado por la aplicación; máximo 3 generaciones por caso |
| Artefactos | Artifact Registry privado: `polar-assistant` |
| Credencial Gemini | Secret Manager habilitado, sin secreto creado ni acceso concedido |
| FIT | No se copió ninguno; futuro bucket privado y montaje de sólo lectura requieren autorización |
| Sesiones | SQLite en `/tmp/polar-adk`; efímeras en esta prueba |
| Auditoría | Simulación; exportar la evidencia antes de que termine la instancia |

Los archivos FIT, `.env`, reportes, bases SQLite y el historial Git no forman
parte del contexto de construcción. `.dockerignore` y `.gcloudignore` usan una
lista explícita de archivos permitidos.

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

## Próxima prueba integrada, con autorización específica

1. Guardar la clave directamente en Secret Manager sin imprimirla y conceder
   lectura sólo a `polar-sport-runtime`.
2. Copiar únicamente los FIT autorizados a un bucket privado y conceder al
   runtime lectura de esos objetos. No incorporarlos a la imagen.
3. Crear una revisión nueva con el secreto y el montaje explícitos. Conservar el
   digest de la imagen y la configuración de revisión como evidencia.
4. Abrir un caso cloud nuevo y ejecutar el flujo completo. La aprobación del
   caso local anterior no autoriza el caso cloud.

La autorización de infraestructura no cubre estos cuatro pasos ni el envío de
información biométrica a este destino. Si se autoriza la prueba con datos
reales, guardar la clave directamente en Secret Manager sin imprimirla; copiar
solamente los FIT requeridos al bucket privado y otorgar al runtime lectura del
secreto y de esos objetos.

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
