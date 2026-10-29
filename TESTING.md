# Pruebas automatizadas

## Inventario actual

La suite actual contiene **97 casos de prueba**. El número es el resultado de
`pytest --collect-only -q`: no representa 93 sesiones manuales ni 93 llamadas
a Gemini. Un archivo puede producir varios casos mediante `pytest.mark.parametrize`.

| Grupo | Casos | Qué valida | Tipo |
|---|---:|---|---|
| `test_bounded_workflow.py` | 31 | Presupuesto máximo de tres llamadas, validación de JSON, aprobación humana, rutas de bloqueo, bienvenida `AWAITING_INTENT` y resumen de última sesión. | Integración local: ADK Runner real, sesión en memoria y gateway simulado. |
| `test_outbound_summary.py` | 22 | Contrato Pydantic 1.1, unidades, zonas, límites y exclusión de muestras crudas. | Unidad / contrato. |
| Rutas (`test_route_dispatcher.py`, `unit/test_workflow_routing.py`) | 7 | Prioridad de seguridad, calidad de datos y ruta de recomendación. | Unidad e integración local. |
| Telemetría y dominio | 9 | Comparación de sesiones, métricas, demo cloud y adaptadores FIT. | Unidad; algunos casos leen sólo los FIT demo locales configurados. |
| Polar AccessLink y OAuth | 9 | Selección de sesión y errores HTTP/OAuth controlados. | Unidad con dobles de prueba; sin llamada remota. |
| Composición y configuración | 8 | Jerarquía ADK, memoria local y cliente Vertex sin API key. | Unidad con variables y clientes simulados. |
| Sesión curada, Dynamic v4 y compatibilidad v3 | 7 | Allowlist, zonas y duraciones, ID estable, rechazo de payload inválido, consulta limitada al sujeto autenticado y solicitud v4 de `features=zones`. | Unidad / contrato; repositorio en memoria. |
| Repositorio Firestore curado | 4 | Última sesión, orden descendente, límite, colección vacía, aislamiento de sujeto y documento inválido. | Unidad con cliente Firestore falso; sin llamada remota. |

Los grupos suman 97. Las siete pruebas del contrato curado y las cuatro del
repositorio Firestore validan la frontera de datos; no contactan Polar,
Firestore ni BigQuery.

Además de la suite, el 29 de octubre de 2026 se ejecutó la verificación manual
`scripts/firestore_curated_smoke.py` contra Firestore Native: cinco sesiones
AccessLink v3 autorizadas, cinco documentos leídos tras *upserts* idempotentes
y 25 períodos de zona preservados. No forma parte de `pytest`, porque requiere
consentimiento Polar y ADC con permiso de escritura.

El mismo día, `scripts/firestore_curated_query_smoke.py` inyectó un cliente REST
con ADC en `FirestoreCuratedSessionRepository` y leyó los cinco documentos en
orden descendente por `started_at`, todos con períodos de zona. Es evidencia de
la consulta técnica del sujeto de prueba; no activa la consulta en ADK Web.

## Ejecución

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q
```

La primera orden informa el inventario. La segunda ejecuta la suite. Las
advertencias actuales de `fitparse` por `utcfromtimestamp` son deprecaciones
de la dependencia; no son fallos de los 93 casos.

## Qué estas pruebas sí demuestran

- El flujo controlado usa ADK Runner y conserva el estado de sesión en los
  escenarios cubiertos.
- Un saludo no carga telemetría ni consume Gemini; la opción `1` no consume
  Gemini y sólo resume la fuente disponible.
- Los bloqueos de seguridad y calidad no realizan llamadas al gateway del
  modelo en los casos simulados.
- El contrato que cruza la frontera Python → Gemini limita campos, tamaños y
  estructura antes de construir la solicitud.
- La identidad Vertex se configura sin leer `GOOGLE_API_KEY` ni
  `GEMINI_API_KEY`.

## Qué no demuestran

- No realizan llamadas reales a Gemini, Vertex AI, Polar AccessLink ni OAuth.
- No verifican por sí mismas el inicio de sesión IAP, la disponibilidad de
  Cloud Run, costos, rendimiento remoto ni persistencia entre instancias.
- No certifican resultados deportivos, médicos ni el significado de una
  recomendación.

Para la infraestructura y la verificación manual de Cloud Run, consulta
[`deploy/README.md`](deploy/README.md). Para el contrato de datos enviado al
modelo, consulta [`specs/OUTBOUND_MODEL_DATA_CONTRACT.md`](specs/OUTBOUND_MODEL_DATA_CONTRACT.md).
Los reportes bajo `reports/qa_payload_*` son evidencia histórica: indican el
conteo de su ejecución concreta y no sustituyen este inventario actual.
