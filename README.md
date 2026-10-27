# PolarVeritySense

Repositorio público oficial: https://github.com/RobertMX23/PolarVeritySense.
Consulta el [contrato de publicación pública](specs/PUBLIC_REPOSITORY_CONTRACT.md)
antes de añadir datos, ejemplos o automatizaciones.

## QA en Cloud Run

Agente Python con Google ADK: ingesta y cálculos en Python, resumen Pydantic
1.1, analista y crítico Gemini, aprobación humana ligada a caso/propuesta y
auditoría de simulación. Máximo tres generaciones por caso.

Esta copia seleccionada del código actual excluye datos personales y evidencia
de ejecución. El historial y los cambios del repositorio local original permanecen intactos.
Se excluyen credenciales, FIT, reportes personales, documentos de trabajo y
pruebas que dependen de telemetría real. No hay despliegue automático ni triggers.

## Ejecución y despliegue

Ver [la preparación de Cloud Run](deploy/README.md). El contenedor usa el mismo
`root_agent`; para el ensayo real necesita un montaje FIT autorizado y una
credencial Gemini suministrada fuera de la imagen. El servicio deberá ser
privado y sus sesiones locales son efímeras.

## Pruebas sin datos personales

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r deploy/requirements.txt pytest
.\.venv\Scripts\python.exe -m pytest -q
```

Estas pruebas usan fixtures controlados y gateways simulados; no son evidencia
de llamadas reales a Gemini ni de un despliegue remoto completado. La suite
completa de la copia local requiere archivos privados que no se publican aquí.
