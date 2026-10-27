# Contrato de publicación pública

## Identidad y alcance

El repositorio canónico es **PolarVeritySense**, publicado en
https://github.com/RobertMX23/PolarVeritySense. Su finalidad es compartir el
código, contratos, pruebas sin datos personales y configuración reproducible
del asistente deportivo basado en Polar, Python, Google ADK y Gemini.

Una contribución no autoriza consultas a Polar, llamadas a Gemini, despliegues
en Cloud Run ni cambios a un plan de entrenamiento. Cada acción externa
conserva su propia autorización y sus controles de aprobación humana.

## Contenido permitido

- Código fuente, contratos de interfaz y documentación técnica.
- Pruebas con fixtures sintéticos o mínimos que no identifiquen a una persona.
- Configuración de ejemplo con valores vacíos o marcadores.
- Definiciones de imagen y despliegue que excluyan datos y secretos del contexto de construcción.

## Contenido prohibido

- Claves API, tokens OAuth, secretos de cliente, archivos `.env`, certificados o credenciales.
- FIT, series crudas de frecuencia cardiaca, exportaciones de Polar Flow, identificadores de sesión, rutas locales, fechas de ejercicio o contexto personal.
- Reportes con evidencia personal, SQLite, artefactos ADK, historiales de conversación o documentos privados.

## Reglas de contribución

1. Mantener `.gitignore`, `.dockerignore` y `.gcloudignore` con exclusiones coherentes.
2. Revisar antes de publicar el diff, archivos nuevos y patrones de credenciales.
3. Guardar telemetría y auditorías personales fuera de Git. Publicar sólo resultados agregados autorizados.
4. Usar secretos administrados por el destino de ejecución; nunca incluirlos en imágenes, builds ni commits.
5. Mantener Cloud Run privado mediante IAM. El código público no hace públicos el endpoint, el bucket de FIT ni los logs.

## Si aparece información sensible

Detener la publicación, revocar o rotar la credencial afectada y retirar el
archivo de la rama. Si llegó a GitHub, revisar el historial y coordinar una
limpieza antes de considerar cerrado el incidente. La visibilidad pública no
sustituye la revocación de una credencial ni borra copias existentes.
