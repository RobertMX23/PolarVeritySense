# PolarVeritySense

Repositorio público oficial: https://github.com/RobertMX23/PolarVeritySense.
Consulta el [contrato de publicación pública](specs/PUBLIC_REPOSITORY_CONTRACT.md)
antes de añadir datos, ejemplos o automatizaciones.

## QA en Cloud Run

Agente Python con Google ADK: ingesta y cálculos en Python, resumen Pydantic
1.1, analista y crítico Gemini, aprobación humana ligada a caso/propuesta y
auditoría de simulación. Máximo tres generaciones por caso.

Esta copia seleccionada del código actual excluye datos personales y evidencia
de ejecución.
Se excluyen credenciales, FIT, reportes personales, documentos de trabajo y
pruebas que dependen de telemetría real. No hay despliegue automático ni triggers.

## Ejecución y despliegue

Ver [la preparación de Cloud Run](deploy/README.md). El contenedor usa el mismo
`root_agent`; para el ensayo real necesita un montaje FIT autorizado y una
credencial Gemini suministrada fuera de la imagen. El servicio deberá ser
privado y sus sesiones locales son efímeras.

## Infraestructura como código

La configuración reproducible está en [infra/terraform](infra/terraform/README.md).
Adopta el servicio privado ya desplegado, el registro de imágenes, las APIs y
la cuenta de ejecución. El estado vive en un bucket privado versionado; los
archivos de estado, `backend.hcl` y valores locales no se publican.

## Flujo ADK 2.x

La comparación con los patrones oficiales de ADK 2.x está en
[ADK_2_WORKFLOW_ALIGNMENT.md](ADK_2_WORKFLOW_ALIGNMENT.md). El flujo conserva
agentes personalizados para aplicar rutas condicionales, límite de tres
generaciones y aprobación humana sin delegación implícita.
La referencia de grafos y la tabla cruzada están en
[ADK_GRAPH_WORKFLOW_EVALUATION.md](ADK_GRAPH_WORKFLOW_EVALUATION.md).
El prompt de implementación controlada está en
[ADK_GRAPH_IMPLEMENTATION_PROMPT.md](ADK_GRAPH_IMPLEMENTATION_PROMPT.md).
La arquitectura de conexión de Polar, Firestore y BigQuery está en
[DATA_CONNECTION_ARCHITECTURE.md](DATA_CONNECTION_ARCHITECTURE.md).
El inventario actual de pruebas está en [TESTING.md](TESTING.md).

## Inicio de conversación

Un saludo breve, por ejemplo `hola`, deja la sesión en `AWAITING_INTENT`.
El asistente ofrece revisar la última sesión disponible, comparar sesiones o
pedir una recomendación y espera una segunda respuesta. La opción `1` usa
Python para devolver el resumen de la sesión disponible, sin Gemini; las demás
respuestas inician el caso acotado.

## Pruebas sin datos personales

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r deploy/requirements.txt pytest
.\.venv\Scripts\python.exe -m pytest -q
```

Estas pruebas usan fixtures controlados y gateways simulados; no son evidencia
de llamadas reales a Gemini ni de un despliegue remoto completado. La suite
completa de la copia local requiere archivos privados que no se publican aquí.
