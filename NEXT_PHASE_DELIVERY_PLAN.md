# Plan de entrega siguiente — datos curados e identidad

**Actualizado:** 2026-10-29  
**Ámbito:** evolución del entorno privado de QA, no publicación de un producto
médico ni una aplicación móvil.

## Foco de la siguiente iteración

La iteración se limita a demostrar y endurecer el recorrido controlado
**Polar AccessLink local → contrato Pydantic curado → Firestore → consulta
técnica verificable**. Trabajará con la autorización local ya existente y el
sujeto técnico de prueba; no sustituye todavía la identidad de una persona ni
convierte la aplicación de Cloud Run en un servicio de datos personales.

OAuth cloud multiusuario, Secret Manager, el vínculo IAP → `subject_id` y el
despliegue de una imagen que lea Firestore se mantienen como la entrega
posterior. Son dependencias de producto y seguridad, no requisitos para
terminar la validación local de datos curados.

El prompt de implementación con archivos, ajuste de código y límites está en
[PROMPT_PHASE1_POLAR_FIRESTORE_LOCAL.md](prompts/PROMPT_PHASE1_POLAR_FIRESTORE_LOCAL.md).

## Punto de partida verificado

| Capacidad | Estado comprobado | Límite vigente |
|---|---|---|
| Agente ADK en Cloud Run | Desplegado, privado por IAP, con Vertex AI mediante ADC. | La revisión activa aún responde con `synthetic_cloud_demo`. |
| Flujo de bienvenida | El saludo deja la sesión en `AWAITING_INTENT`; la opción `1` muestra un resumen determinista. | No identifica ni consulta una sesión personal en Firestore. |
| Datos Polar | Cinco sesiones AccessLink v3 autorizadas fueron normalizadas. | Dynamic API v4, consentimiento cloud y renovación de token aún no están integrados. |
| Firestore | Native `(default)` en `us-central1`; cinco documentos curados fueron escritos y leídos tras *upserts* idempotentes. | Los documentos están bajo un sujeto técnico de prueba, sin relación IAP/OAuth. |
| Zonas | Se conservaron 25 períodos de zona con límites, duración y calidad de cobertura. | La cobertura de las cinco sesiones es `partial`; nunca se debe completar con valores inventados. |
| Seguridad | Cuenta runtime de sólo lectura y cuenta `polar-sport-sync` de escritura, ambas sin claves gestionadas por usuario. | El sincronizador todavía no está desplegado. |

## Tabla cruzada del alcance y avance

| Línea de trabajo | Alcance original | Estado real | Evidencia actual | Siguiente punto que la desbloquea | Documento de referencia |
|---|---|---|---|---|---|
| Fundamentos Python, Pydantic y pruebas | Fase 0 | Completado | `root_agent`, contratos y 93 pruebas aprobadas. | Mantener regresiones en cada entrega. | `PROJECT_CHECKLIST.md`, `TESTING.md` |
| Demo post-entrenamiento y gobernanza | Fase 1 | Completado para demo | Cálculo determinista, máximo de tres llamadas, crítico y HITL con auditoría simulada. | No extender a cambios externos sin nueva aprobación. | `PROJECT_SCOPE_AND_DEMO_CHECKLIST.md`, `PROJECT_STATUS_2026-10-27.md` |
| Polar AccessLink local | Fase 1 / 3 | Parcial | Cinco sesiones v3 autorizadas y zonas normalizadas. | Repetir lectura, validación, zonas y errores transitorios con la autorización local. | `DATA_CONNECTION_ARCHITECTURE.md` |
| Cloud Run privado | Fase 2 / 3.5 | Completado para QA | IAP, ADC, Vertex AI y revisión privada desplegada. | Mantener IAP al publicar la siguiente imagen. | `deploy/README.md` |
| Inicio guiado ADK Web | Fase 1 / experiencia QA | Completado | `AWAITING_INTENT`; saludo no abre análisis y opción `1` es determinista. | Resolver sujeto autenticado para mostrar datos curados reales. | `README.md`, `TESTING.md` |
| Firestore curado | Fase 2 | Base verificada | Base Native, permisos mínimos, 5 documentos y 25 períodos de zona leídos tras reintentos. | Repositorio de lectura y consulta técnica para el sujeto de prueba. | `DATA_CONNECTION_ARCHITECTURE.md` |
| Identidad y consentimiento | Fase 2 | Pendiente | IAP autentica acceso web, pero no existe vínculo IAP → `subject_id`. | Definir propietario, consentimiento, revocación y aislamiento. | Este plan, tarea 1 |
| Consulta Firestore desde el agente | Fase 2 | Pendiente | Contrato y tool acotada existen, pero la imagen no los compone. | Repositorio por `authenticated_subject_id` y pruebas A/B. | Este plan, tarea 2 |
| Sincronización Polar cloud | Fase 2 | Pendiente | Cuenta `polar-sport-sync` creada sin claves; smoke test usó ADC de operador. | Servicio keyless, OAuth cloud y Secret Manager. | Este plan, tareas 3–4 |
| Nueva revisión Cloud Run con datos reales | Fase 2 | Pendiente | La revisión activa aún usa `synthetic_cloud_demo`. | Completar identidad, lectura y sincronización; construir por digest. | Este plan, tarea 5 |
| Operación, coste y QA extremo a extremo | Fase 2 | Parcial | Logs básicos y límites de instancia; faltan alertas específicas y matriz E2E. | Pruebas de aislamiento, consentimiento, reintentos y presupuesto. | Este plan, tarea 6 |
| BigQuery histórico | Fase 2 posterior | No iniciado intencionalmente | Diseño documental, sin dataset ni tabla. | Validar primero la consulta operativa Firestore. | `DATA_CONNECTION_ARCHITECTURE.md` |
| BLE, móvil, RAG, Memory Bank y Agent Engine | Fases 3–4 | Fuera de la siguiente entrega | Roadmap únicamente. | Priorización posterior al flujo seguro de datos curados. | `PROJECT_SCOPE_AND_DEMO_CHECKLIST.md` |

## Orden de trabajo

| Prioridad | Entrega | Rol responsable | Contexto | Instrucciones | Límites (*boundaries*) | Resultado esperado / evidencia |
|---:|---|---|---|---|---|---|
| 1 | Lectura local AccessLink y curación | Ingeniero de integraciones | Hay cinco sesiones v3 autorizadas y el contrato ya preserva zonas y su calidad. | Ejecutar inventario de sólo lectura, normalizar cada sesión mediante `CuratedTrainingSession`, probar zonas incompletas y errores HTTP transitorios. Registrar conteos y procedencia, sin guardar el payload original. | No ampliar el permiso Polar ni mover el token local a cloud. No inferir tiempo de zona ausente como cero. | Reporte reproducible de sesiones, zonas, calidad y errores controlados; pruebas de contrato ampliadas. |
| 2 | Escritura Firestore curada local | Ingeniero backend + integraciones | La base y los permisos existen; el smoke test ya verificó cinco documentos y 25 períodos de zona. | Repetir el *upsert* desde AccessLink local, validar ID estable, lectura posterior y orden por `started_at` para el sujeto técnico `ath_local_smoke_2026`. | Persistir sólo allowlist curada. No guardar token, payload crudo, muestras, notas, ubicación ni una identidad real. | Ejecución repetible que mantiene el mismo número de documentos tras reintentos y confirma zonas, duración y calidad. |
| 3 | Repositorio y consulta técnica Firestore | Ingeniero backend | Existe la tool acotada y el runtime posee permiso de lectura, pero la imagen aún no compone el repositorio. | Implementar y probar un repositorio Firestore de lectura para el sujeto técnico explícito de desarrollo; listar, obtener última sesión y devolver la proyección permitida. | Es una herramienta de desarrollo, no una ruta expuesta al chat ni un sustituto de identidad autenticada. El LLM no recibe cliente Firestore ni IDs arbitrarios. | Pruebas de orden, ausencia de datos, aislamiento A/B simulado y lectura de los documentos de prueba. |
| 4 | Validación local extremo a extremo | QA | Deben coincidir lo leído de AccessLink, lo curado y lo recuperado desde Firestore. | Comparar IDs, fecha, modalidad, FC, cobertura de zonas y períodos antes/después del almacenamiento. Medir duración de lectura, curación, escritura y consulta. | No atribuir la medición local a rendimiento del agente ni a una garantía clínica. | Matriz de evidencia con cinco sesiones, discrepancias cero o explicadas y límites documentados. |
| 5 | Identidad interna y consentimiento | Responsable de producto + seguridad | Firestore contiene un sujeto técnico y IAP autentica el navegador, sin vínculo de atleta. | Definir `subject_id` opaco, consentimiento, revocación y vínculo con identidad IAP verificada. | No usar correo Google, `x_user_id` de Polar ni texto del chat como clave. No migrar datos de prueba a una identidad real. | Especificación aprobada y pruebas de aislamiento. |
| 6 | Sincronizador OAuth cloud y Secret Manager | Seguridad + integraciones | El token local v3 demuestra compatibilidad, no operación multiusuario. | Configurar OAuth cloud, callback, renovación y sincronizador keyless bajo `polar-sport-sync`. | El runtime interactivo no puede leer secretos; no crear claves de cuenta de servicio ni registrar tokens. | Consentimiento y renovación verificadas con secreto fuera del repositorio. |
| 7 | Composición ADK y nueva revisión Cloud Run | Ingeniero ADK / plataforma | La revisión activa aún usa `synthetic_cloud_demo`. | Después de las tareas 5–6, componer el repositorio usando el sujeto autenticado, construir por digest y desplegar con IAP. | Mantener fallback demo, fuente explícita y acceso privado. | ADK Web muestra sólo sesiones del sujeto vinculado o un estado vacío claro. |
| 8 | Histórico analítico opcional | Ingeniería de datos | BigQuery no está creado. | Evaluarlo sólo tras validar la ruta Firestore. | Sin SQL generado por el modelo ni uso en la respuesta interactiva normal. | Diseño de retención, IAM y consulta parametrizada. |

## Criterios de salida de la siguiente entrega

La iteración actual termina cuando las tareas 1 a 4 producen estas evidencias:

1. AccessLink local devuelve sesiones que se normalizan sin perder las zonas ni
   convertir la ausencia de duración en un valor inventado.
2. Firestore conserva exactamente los documentos curados después de reintentos
   y permite verificar orden, fecha, procedencia, zonas y cobertura.
3. El repositorio técnico devuelve únicamente la proyección permitida para el
   sujeto de prueba y falla de forma clara si no existen datos.
4. La evidencia E2E compara AccessLink local, contrato curado y Firestore sin
   almacenar tokens ni payloads crudos.

## Fuera del alcance de esta entrega

- Asociación IAP/OAuth de una persona a un sujeto de Firestore.
- OAuth cloud multiusuario, Secret Manager y sincronización desplegada.
- Nueva revisión Cloud Run que consulte Firestore.
- Bluetooth y captura en vivo desde Polar Verity Sense.
- Aplicaciones Android, iOS o web de usuario final.
- Firestore como repositorio de muestras biométricas crudas.
- BigQuery, RAG, Memory Bank, Agent Engine y MCP como dependencias necesarias
  para que el agente consulte la última sesión.
- Diagnóstico clínico, recomendaciones farmacológicas o actualización
  automática de entrenamiento.

## Dependencias de la entrega posterior

Antes de iniciar las tareas 5 a 7 hace falta decidir quién puede asociar una
cuenta IAP a un atleta, qué consentimiento se registra, cuánto tiempo se
retienen los resúmenes curados y cómo se revoca el acceso. Estas decisiones no
pueden ser sustituidas por una inferencia del agente.
