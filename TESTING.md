# Pruebas automatizadas

## Inventario actual

La suite actual contiene **90 casos de prueba**. El número es el resultado de
`pytest --collect-only -q`: no representa 90 sesiones manuales ni 90 llamadas
a Gemini. Un archivo puede producir varios casos mediante `pytest.mark.parametrize`.

| Grupo | Casos | Qué valida | Tipo |
|---|---:|---|---|
| `test_bounded_workflow.py` | 31 | Presupuesto máximo de tres llamadas, validación de JSON, aprobación humana, rutas de bloqueo, bienvenida `AWAITING_INTENT` y resumen de última sesión. | Integración local: ADK Runner real, sesión en memoria y gateway simulado. |
| `test_outbound_summary.py` | 22 | Contrato Pydantic 1.1, unidades, zonas, límites y exclusión de muestras crudas. | Unidad / contrato. |
| Rutas (`test_route_dispatcher.py`, `unit/test_workflow_routing.py`) | 7 | Prioridad de seguridad, calidad de datos y ruta de recomendación. | Unidad e integración local. |
| Telemetría y dominio | 9 | Comparación de sesiones, métricas, demo cloud y adaptadores FIT. | Unidad; algunos casos leen sólo los FIT demo locales configurados. |
| Polar AccessLink y OAuth | 9 | Selección de sesión y errores HTTP/OAuth controlados. | Unidad con dobles de prueba; sin llamada remota. |
| Composición y configuración | 8 | Jerarquía ADK, memoria local y cliente Vertex sin API key. | Unidad con variables y clientes simulados. |
| Sesión curada y tool | 4 | Allowlist Dynamic API v4, ID estable, rechazo de payload inválido y consulta limitada al sujeto autenticado. | Unidad / contrato; repositorio en memoria. |

Los grupos suman 90. Las cuatro pruebas más recientes validan el contrato de
sesión curada y su tool de consulta; no contactan Polar, Firestore ni BigQuery.

## Ejecución

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q
```

La primera orden informa el inventario. La segunda ejecuta la suite. Las
advertencias actuales de `fitparse` por `utcfromtimestamp` son deprecaciones
de la dependencia; no son fallos de los 90 casos.

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
