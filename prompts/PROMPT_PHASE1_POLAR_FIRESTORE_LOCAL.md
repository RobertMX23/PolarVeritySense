# Prompt de implementación — Polar AccessLink local y Firestore curado

> **Estado de ejecución:** aplicado el 2026-10-29. Se entregó el repositorio
> técnico de lectura, cuatro pruebas nuevas y una consulta ADC exitosa de los
> cinco documentos de prueba. Este prompt permanece como especificación de
> revisión y para futuras iteraciones de la misma frontera.

## Rol

Actúa como **ingeniero senior de integración Python y persistencia de datos**.
Trabaja en el repositorio `PolarVeritySense`. Tu objetivo es cerrar la
iteración técnica local: leer las sesiones ya autorizadas en Polar AccessLink
v3, normalizarlas con el contrato Pydantic existente, conservarlas en Firestore
y demostrar una consulta técnica limitada al sujeto de prueba.

## Contexto comprobado

- AccessLink v3 devuelve cinco sesiones autorizadas con zonas; las duraciones
  de zona pueden ser parciales y una duración ausente significa `None`, nunca
  cero.
- Firestore Native `(default)` ya existe en `us-central1`.
- Cinco documentos curados se escribieron y leyeron mediante *upserts*
  idempotentes. Se preservaron 25 períodos de zona.
- La cuenta runtime tiene lectura y `polar-sport-sync` tiene escritura. La
  prueba actual usa ADC del operador y no crea claves de cuenta de servicio.
- La revisión activa de Cloud Run aún usa `synthetic_cloud_demo`. Esta tarea no
  cambia ese comportamiento.

## Diagnóstico del código actual

| Archivo | Código actual | Ajuste requerido |
|---|---|---|
| `src/polar_assistant/application/curated_sessions.py` | `CuratedTrainingSession`, `CuratedZonePeriod`, curación v3 y `CuratedSessionQueryService` ya definen la allowlist, el ID estable y la consulta de dominio. | No ampliar el contrato con datos crudos. Reutilizarlo como única frontera de datos. |
| `src/polar_assistant/infrastructure/curated_session_store.py` | Contiene repositorio en memoria, writer y `FirestoreCuratedSessionRepository` de lectura con cliente inyectado. | Mantener la ruta `athletes/{subject_id}/sessions`, la validación `CuratedTrainingSession`, el orden descendente y el límite; no mover la identidad a esta capa. |
| `sport_assistant_agent/curated_data_tools.py` | La tool exige `authenticated_subject_id` y nunca acepta el sujeto desde el chat. | No cambiar su frontera de identidad ni conectarla a `agent.py` en esta iteración. Probar el repositorio debajo del servicio de consulta. |
| `scripts/polar_v3_inventory.py` | Consulta AccessLink en sólo lectura con `samples=false` y `zones=true`. | Mantener la lectura minimizada; ampliar sólo errores transitorios controlados si es necesario. |
| `scripts/polar_v3_curated_smoke.py` | Demuestra curación e idempotencia únicamente en memoria. | Mantenerla como contrato local; no convertirla en mecanismo cloud. |
| `scripts/firestore_curated_smoke.py` y `scripts/firestore_curated_query_smoke.py` | El primero escribe/relee; el segundo ejecuta consulta técnica REST mediante el repositorio inyectado. | Mantener ambos separados: escritura curada y lectura técnica verificable. |
| `tests/test_curated_sessions.py` | Cubre allowlist, zonas v3/v4, ID estable y servicio de consulta en memoria. | Añadir pruebas del repositorio Firestore con dobles de cliente: orden, límite, documento inválido, colección vacía y aislamiento de sujeto. |

## Instrucciones

1. **Diseña el adaptador de lectura.** En
   `src/polar_assistant/infrastructure/curated_session_store.py`, implementa
   `FirestoreCuratedSessionRepository` con una dependencia de cliente
   inyectada. Debe implementar `latest_for_subject()` y
   `list_for_subject(subject_id, limit=...)` del protocolo existente.
2. **Delimita la consulta.** El adaptador sólo puede recorrer
   `athletes/{subject_id}/sessions`; debe ordenar por `started_at` descendente y
   limitar en la consulta y/o en memoria defensivamente. Nunca debe consultar
   una colección global ni aceptar un filtro construido desde texto de usuario.
3. **Valida antes de devolver.** Cada documento leído se transforma mediante
   `CuratedTrainingSession.model_validate`. Si un documento no cumple el
   contrato, devuelve un error explícito de infraestructura o una excepción
   controlada; no corrijas silenciosamente campos ni inventes zonas.
4. **Mantén los tipos de fecha.** El adaptador debe aceptar los valores que
   devuelve el cliente oficial de Firestore (`datetime`) y los valores de los
   dobles de prueba. `started_at` se conserva como instante con zona horaria.
5. **Prueba el adaptador.** Crea pruebas específicas con un cliente falso que
   registre la ruta solicitada. Demuestra: última sesión correcta, orden
   descendente, `limit`, ausencia de sesiones, aislamiento entre dos sujetos y
   rechazo de un documento inválido.
6. **Crea una verificación técnica opcional.** Si hace falta para ejercitar la
   lectura real, añade `scripts/firestore_curated_query_smoke.py`. Debe usar
   ADC, requerir explícitamente `--project-id` y `--subject-id`, imprimir sólo
   conteos, IDs curados y metadatos permitidos, y no imprimir token ni payload
   raw. No ejecutes esa verificación sin autorización explícita del operador.
7. **Actualiza la documentación.** Ajusta
   `DATA_CONNECTION_ARCHITECTURE.md`, `TESTING.md` y
   `NEXT_PHASE_DELIVERY_PLAN.md` para indicar que la consulta es técnica para
   el sujeto de prueba y no está compuesta en Cloud Run ni expuesta al chat.
8. **Valida.** Ejecuta como mínimo:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests\test_curated_sessions.py -q
   .\.venv\Scripts\python.exe -m pytest -q
   ```

   Ejecuta una lectura real de Firestore sólo si existe autorización separada
   para consultar los documentos de prueba mediante ADC.

## Límites (*boundaries*)

- No modificar `sport_assistant_agent/agent.py`, el despliegue de Cloud Run,
  Terraform, IAP, OAuth cloud, Secret Manager o el `Dockerfile`.
- No usar el correo de Google, `x_user_id` de Polar ni un mensaje de usuario
  como `subject_id`.
- No leer, imprimir, persistir ni enviar al modelo tokens OAuth, secretos,
  payloads Polar completos, muestras de señal, ubicación, notas o datos de
  perfil físico.
- No añadir una API pública, acceso `allUsers`, una clave de servicio ni una
  dependencia cloud innecesaria en las capas de dominio o aplicación.
- No cambiar `partial` o `unavailable` a `complete`, ni convertir una duración
  desconocida en `0`.
- No afirmar que la consulta técnica ya es una función disponible para un
  usuario autenticado de ADK Web.

## Resultado esperado

La entrega estará completa cuando exista un repositorio Firestore de lectura
probado y limitado al sujeto técnico, el contrato curado se conserve intacto,
las pruebas pasen y la documentación distinga claramente entre:

1. la ruta local verificada AccessLink → Pydantic → Firestore → consulta
   técnica, y
2. la futura ruta de producto con identidad, consentimiento, sincronización
   cloud y composición en Cloud Run.
