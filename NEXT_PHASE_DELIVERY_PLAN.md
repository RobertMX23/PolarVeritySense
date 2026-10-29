# Plan de entrega siguiente — datos curados e identidad

**Actualizado:** 2026-10-29  
**Ámbito:** evolución del entorno privado de QA, no publicación de un producto
médico ni una aplicación móvil.

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
| Polar AccessLink local | Fase 1 / 3 | Parcial | Cinco sesiones v3 autorizadas y zonas normalizadas. | Consentimiento cloud, renovación y sincronizador keyless. | `DATA_CONNECTION_ARCHITECTURE.md` |
| Cloud Run privado | Fase 2 / 3.5 | Completado para QA | IAP, ADC, Vertex AI y revisión privada desplegada. | Mantener IAP al publicar la siguiente imagen. | `deploy/README.md` |
| Inicio guiado ADK Web | Fase 1 / experiencia QA | Completado | `AWAITING_INTENT`; saludo no abre análisis y opción `1` es determinista. | Resolver sujeto autenticado para mostrar datos curados reales. | `README.md`, `TESTING.md` |
| Firestore curado | Fase 2 | Base verificada | Base Native, permisos mínimos, 5 documentos y 25 períodos de zona leídos tras reintentos. | Identidad interna y repositorio de lectura en runtime. | `DATA_CONNECTION_ARCHITECTURE.md` |
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
| 1 | Identidad interna y consentimiento | Responsable de producto + seguridad | Firestore contiene `ath_local_smoke_2026`; IAP autentica al navegador, pero no existe vínculo con una persona o atleta. | Definir un `subject_id` opaco, una tabla o perfil de vínculo y el ciclo de consentimiento/revocación. Documentar cómo se obtiene la identidad IAP verificada antes de llegar al agente. | No usar correo de Google, `x_user_id` de Polar ni texto del chat como clave de Firestore. No migrar los documentos de prueba a una identidad real. | Especificación aprobada de identidad, diagrama de flujo y pruebas de aislamiento por sujeto. |
| 2 | Repositorio Firestore de lectura | Ingeniero backend | El contrato `CuratedTrainingSession` y la tool acotada ya existen; Cloud Run posee `roles/datastore.viewer`. | Implementar un repositorio que liste y obtenga la última sesión sólo para el `authenticated_subject_id` verificado. Ordenar por `started_at`, limitar resultados y devolver únicamente la proyección permitida. Añadir dobles de prueba. | El LLM no recibe un cliente Firestore, SQL, identificador de sujeto elegido por el usuario, tokens Polar ni payload crudo. | Pruebas unitarias de orden, ausencia de datos y aislamiento A/B; tool devuelve `NO_CURATED_SESSION` o una sesión del sujeto autenticado. |
| 3 | Sincronizador Polar keyless | Ingeniero de integraciones | La cuenta `polar-sport-sync` ya tiene escritura Firestore; la prueba actual usa ADC de operador y AccessLink v3 local. | Diseñar y desplegar un proceso de sincronización separado, con ejecución bajo esa cuenta. Tras consentimiento, obtener sesiones, normalizar con Pydantic, hacer *upsert* por `session_id` y registrar procedencia. | No guardar tokens OAuth en Firestore, logs, ADK state, Git ni variables de imagen. No crear claves de cuenta de servicio. No persistir series crudas, ubicación o notas. | Una ejecución programada o manual autenticada que sincroniza un atleta de prueba, con log de conteos y prueba de reintento idempotente. |
| 4 | Gestión de secretos y OAuth cloud | Seguridad + integraciones | El token local v3 sólo demuestra compatibilidad; no es multiusuario. | Configurar el cliente OAuth de Polar, callback permitido, Secret Manager y renovación. Diseñar la referencia cifrada de token por sujeto y los permisos mínimos del sincronizador. | El runtime interactivo de Cloud Run no puede leer el secreto ni renovar tokens. Ningún secreto va a Terraform state, PR, documentación o `.env` de producción. | Prueba de consentimiento y renovación con secreto en Secret Manager; escaneo de secretos aprobado. |
| 5 | Composición del agente y nueva revisión Cloud Run | Ingeniero ADK / plataforma | Firestore ya existe, pero la imagen activa usa datos sintéticos. | Conectar el repositorio de lectura a la composición de la aplicación después de que las tareas 1–2 estén aprobadas. Construir imagen inmutable, actualizar sólo su digest en Terraform y desplegar una nueva revisión privada. | No eliminar el fallback `synthetic_cloud_demo`; etiquetar siempre la fuente. No habilitar acceso público ni cambiar IAP. | ADK Web, con un usuario de prueba vinculado, muestra la última sesión curada y sus zonas; sin usuario vinculado mantiene la demo o devuelve estado vacío claro. |
| 6 | Prueba extremo a extremo y operación | QA + responsable de producto | Deben coexistir rutas demo y real sin mezclar datos. | Ejecutar casos de bienvenida, sesión inexistente, última sesión, comparación, recomendación, rechazo de consentimiento y reintento de sincronización. Medir latencia por etapa y revisar logs. Configurar presupuesto y alertas de facturación. | No medir datos clínicos ni prometer consejo médico. No considerar una respuesta del modelo como evidencia de escritura. | Matriz de pruebas firmada, evidencia de una sesión real curada, tablero/alerta de coste y runbook de incidente. |
| 7 | Histórico analítico opcional | Ingeniería de datos | Firestore cubre consultas operativas; BigQuery no está creado. | Sólo tras validar valor y retención, crear dataset y tabla particionada para agregados históricos y evaluaciones. | No usar BigQuery en la respuesta interactiva normal; no permitir SQL generado por el modelo. | Diseño de retención, IAM por dataset y prueba de consulta parametrizada. |

## Criterios de salida de la siguiente entrega

La siguiente entrega termina cuando las tareas 1 a 6 producen estas evidencias:

1. La identidad autenticada se traduce a un `subject_id` interno sin exponer
   correo ni identificadores del proveedor al modelo.
2. El agente consulta exclusivamente documentos del sujeto autenticado y puede
   explicar la fuente y calidad del dato.
3. Una sincronización autorizada guarda registros curados sin secretos ni
   payloads crudos y es idempotente ante reintentos.
4. La nueva imagen de Cloud Run continúa privada con IAP, conserva el fallback
   demo y supera la suite automatizada y los escenarios manuales definidos.
5. El flujo no realiza diagnósticos médicos ni actualiza planes externos sin
   la aprobación humana ya definida.

## Fuera del alcance de esta entrega

- Bluetooth y captura en vivo desde Polar Verity Sense.
- Aplicaciones Android, iOS o web de usuario final.
- Firestore como repositorio de muestras biométricas crudas.
- BigQuery, RAG, Memory Bank, Agent Engine y MCP como dependencias necesarias
  para que el agente consulte la última sesión.
- Diagnóstico clínico, recomendaciones farmacológicas o actualización
  automática de entrenamiento.

## Dependencias de decisión humana

Antes de iniciar las tareas 1, 3 y 4 hace falta decidir quién puede asociar una
cuenta IAP a un atleta, qué consentimiento se registra, cuánto tiempo se
retienen los resúmenes curados y cómo se revoca el acceso. Estas decisiones no
pueden ser sustituidas por una inferencia del agente.
