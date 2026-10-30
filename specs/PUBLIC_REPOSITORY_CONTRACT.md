# Contrato de publicación pública

## Identidad y alcance

El repositorio canónico es **PolarVeritySense**, publicado en
https://github.com/RobertMX23/PolarVeritySense. Su finalidad es compartir el
código, contratos, pruebas sin datos personales y configuración reproducible
del asistente deportivo basado en Polar, Python, Google ADK y Gemini.

Una contribución al repositorio no autoriza consultas a Polar, llamadas a
Gemini, despliegues en Cloud Run ni cambios a un plan de entrenamiento. Cada
acción externa conserva su propia autorización y sus controles de aprobación
humana.

## Contenido permitido

- Código fuente, contratos de interfaz y documentación técnica.
- Pruebas deterministas con fixtures sintéticos o mínimos que no identifiquen a
  una persona.
- Ejemplos de configuración con valores vacíos o marcadores como
  `replace_with_your_google_api_key`.
- Definiciones de imagen y despliegue que excluyan datos y secretos del
  contexto de construcción.

## Contenido prohibido

- Claves API, tokens OAuth, secretos de cliente, archivos `.env`, certificados,
  credenciales de cuenta o salidas que los contengan.
- FIT, series crudas de frecuencia cardiaca, exportaciones de Polar Flow,
  identificadores de sesiones, rutas locales, fechas de ejercicio o contexto
  personal de sueño/fatiga.
- Reportes de ejecución con evidencia personal, bases SQLite, artefactos de
  sesiones ADK, historiales de conversación o documentos privados de trabajo.
- Datos que permitan identificar directamente a una persona aun cuando el
  formato no sea `.fit`.

## Reglas de contribución

1. Mantener `.gitignore`, `.dockerignore` y `.gcloudignore` con exclusiones
   coherentes para datos, reportes, secretos y estado de ejecución.
2. Revisar antes de cada publicación el diff, archivos nuevos y patrones de
   credenciales. No usar una clave real como dato de prueba.
3. Guardar la telemetría y las auditorías personales fuera de Git, bajo las
   rutas locales ignoradas. Si se necesita demostrar un caso, documentar sólo
   resultados agregados que hayan sido aprobados para publicación.
4. Usar secretos administrados por el destino de ejecución. Ningún secreto se
   incorpora a una imagen, un Dockerfile, una variable de build ni un commit.
5. Mantener el servicio de QA de Cloud Run privado mediante IAM. Que el código
   sea público no hace público el endpoint, el bucket de FIT ni los logs.

## Si aparece información sensible

Detener la publicación, revocar o rotar la credencial afectada y retirar el
archivo de la rama. Si llegó a GitHub, revisar el historial y coordinar una
limpieza de historial antes de considerar el incidente cerrado. Cambiar la
visibilidad del repositorio no sustituye la revocación de una credencial ni
borra copias existentes.
