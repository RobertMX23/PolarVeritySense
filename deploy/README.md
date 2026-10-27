# Cloud Run: entorno privado de QA

Destino preparado: proyecto `polar-verity-robertmx23-2026`, región
`us-central1`, servicio previsto `polar-sport-assistant`.
Repositorio privado: https://github.com/RobertMX23/PolarVeritySense.

El proyecto existe, pero el servicio todavía no está desplegado. La facturación
no está vinculada. La imagen local inicia ADK 2.12.0 con Python 3.13.18,
importa el mismo `SportAssistantRoot` y responde a `/version`, `/list-apps` y al
grafo de la aplicación. Estas comprobaciones no ejecutan Gemini ni prueban la
ingesta real.

## Configuración propuesta

| Recurso | Configuración |
|---|---|
| Cloud Run | Servicio privado; autenticación IAM obligatoria |
| Capacidad | 1 CPU, 512 MiB, mínimo 0, máximo 1 instancia, concurrencia 1 |
| Peticiones | Puerto 8080; timeout 300 segundos |
| Imagen | Linux amd64; usuario sin privilegios; mismo `root_agent` |
| Modelos | Gemini configurado por la aplicación; máximo 3 generaciones por caso |
| Artefactos | Artifact Registry privado: `polar-assistant` |
| Credencial Gemini | Secret Manager; permiso de lectura sólo al runtime |
| FIT, si se autoriza su copia | Bucket privado; montaje de sólo lectura en `/mounts/polar-fit` |
| Sesiones | SQLite en `/tmp/polar-adk`; efímeras en esta prueba |
| Auditoría | Simulación; exportar la evidencia antes de que termine la instancia |

La facturación, el almacenamiento de la clave en Secret Manager y la copia de
FIT reales requieren autorización específica para este destino. Los archivos
FIT, `.env`, reportes, bases SQLite y el historial Git no forman parte del
contexto de construcción. `.dockerignore` y `.gcloudignore` usan una lista
explícita de archivos permitidos.

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

## Secuencia de despliegue, después de autorización

1. Vincular la cuenta de facturación elegida al proyecto indicado. Usar
   `--project` y `--account` explícitos; no modificar la configuración global.
2. Habilitar Cloud Run, Cloud Build, Artifact Registry y Secret Manager; crear
   el repositorio Docker y una cuenta de servicio dedicada sin roles generales.
3. Ejecutar Cloud Build con `deploy/cloudbuild.yaml`; guardar el ID del build
   y el digest. Publicar sólo el contexto permitido.
4. Si se autoriza la prueba con datos reales, guardar la clave directamente en
   Secret Manager sin imprimirla; copiar sólo los dos FIT requeridos al bucket
   privado y otorgar al runtime lectura del secreto y de esos objetos.
5. Desplegar el digest con `--no-allow-unauthenticated`, cuenta dedicada,
   `--min=0 --max=1 --max-instances=1 --concurrency=1 --cpu=1 --memory=512Mi
   --timeout=300`. Incorporar el secreto y montaje únicamente si se autorizaron.
6. Acceder mediante `gcloud run services proxy polar-sport-assistant
   --project=polar-verity-robertmx23-2026 --region=us-central1 --port=8089`.
   No hacer público ADK Web para facilitar la prueba.
7. Verificar versión y grafo. Abrir un caso cloud nuevo, conservar todos sus
   eventos y solicitar la aprobación humana específica de su propuesta.
   La aprobación del caso local anterior no autoriza el caso cloud.

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
