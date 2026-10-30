# Prompt de implementación: prototipo de Graph Workflow ADK

**Base técnica:** `google-adk==2.12.0` y la evaluación de
[`ADK_GRAPH_WORKFLOW_EVALUATION.md`](ADK_GRAPH_WORKFLOW_EVALUATION.md).

## Conceptos que aplica el prompt

Un **edge** es una arista dirigida: declara qué nodo se ejecuta después de
otro. En ADK se expresa en `Workflow(edges=[...])`. Por ejemplo,
`("START", ingest, compare, router)` representa una cadena ordenada. Una
arista condicional usa un router que devuelve `Event(route="...")` y un
diccionario que asocia cada nombre de ruta con su nodo destino.

La **ejecución paralela** inicia a la vez nodos que son independientes y luego
combina sus resultados. Reduce tiempo de espera, pero no debe usarse si un nodo
requiere la salida del anterior, si comparten estado mutable o si compiten por
un mismo presupuesto. En PolarVeritySense, ingesta, comparación, decisión,
análisis y crítica son secuenciales: cada paso consume la evidencia o el
presupuesto calculado por el anterior. Por eso este prototipo no debe añadir
paralelismo.

## Prompt listo para usar

~~~text
Rol
Eres un arquitecto senior de Python especializado en Google ADK 2.12.0,
workflows basados en grafos y sistemas con controles de seguridad. Trabajas en
el repositorio PolarVeritySense. Antes de modificar código, inspecciona la API
instalada de google-adk 2.12.0 y la documentación oficial de Graph Workflows;
no inventes clases, parámetros ni comportamiento.

Contexto
El agente desplegado construye su flujo en sport_assistant_agent/agent.py con
GovernedWorkflowAgent. Sus etapas son:
1. TelemetryIngestion: código Python determinista que carga y valida datos.
2. SessionComparisonPreparation: código Python determinista que calcula la
   comparación y workflow_decision.
3. WorkflowRouteDispatcher: elige una sola ruta.
4. Rutas de bloqueo: SafetyEscalationResponse o DataQualityReviewResponse,
   sin usar Gemini.
5. Ruta de recomendación: PhysiologyAnalystAgent, SafetyCriticAgent y, sólo
   si el crítico devuelve REVISE, ProposalRefinementAgent.
6. La aprobación humana es una invocación posterior con un comando exacto
   ligado a case_id y proposal_id.

Objetivo
Implementa un prototipo aislado y probado que represente únicamente la parte
determinista de preparación y enrutamiento mediante Workflow(edges=[...]). El
prototipo debe hacer visible esta topología:

START -> TelemetryIngestion -> SessionComparisonPreparation -> route_selector
route_selector -- SAFETY_ESCALATION --> SafetyEscalationResponse
route_selector -- DATA_QUALITY_REVIEW --> DataQualityReviewResponse
route_selector -- RECOVERY_RECOMMENDATION,
                  CONTEXT_LIMITED_RECOMMENDATION,
                  COMPARABLE_TREND_RECOMMENDATION --> RecommendationAndApproval

Instrucciones de implementación
1. Crea un módulo nuevo, por ejemplo
   sport_assistant_agent/graph_workflow_prototype.py. No reemplaces root_agent
   ni modifiques el flujo desplegado durante esta tarea.
2. Usa Workflow y edges de ADK si la API 2.12.0 instalada confirma esa sintaxis.
   Mantén las etapas existentes como nodos reutilizados o adapta su lógica por
   medio de funciones pequeñas; no dupliques reglas de dominio.
3. Implementa route_selector como una función determinista que derive la
   decisión desde el estado permitido y devuelva Event(route=<ruta>). El mapa
   de aristas debe enumerar explícitamente todas las rutas autorizadas.
4. Conserva los contratos actuales de estado: no pongas telemetría cruda ni
   secretos en prompts, mensajes, eventos, logs o estados nuevos. Transporta
   sólo los datos mínimos entre nodos y conserva la allowlist existente.
5. Para la ruta RecommendationAndApproval, reutiliza el comportamiento
   acotado existente. No agregues llamadas al modelo ni cambies sus prompts.
6. Conserva estas invariantes obligatorias:
   - SAFETY_ESCALATION y DATA_QUALITY_REVIEW hacen cero llamadas a Gemini.
   - Cada caso permite como máximo tres llamadas de modelo.
   - Sólo existe un refinamiento y sólo después de REVISE.
   - La aprobación humana conserva el comando exacto, case_id y proposal_id.
   - Ninguna rama realiza cambios externos: la aprobación es simulación local.
7. No uses ejecución paralela, ParallelAgent ni fan-out concurrente. Explica
   en la documentación que los nodos dependen de la salida y del presupuesto
   del nodo anterior. Sólo propón paralelismo futuro si los nodos tienen
   entradas inmutables independientes, no escriben el mismo estado y existe
   una unión determinista de resultados.
8. Agrega pruebas unitarias sin red ni Vertex AI que cubran:
   - cada ruta autorizada;
   - ausencia de modelo en bloqueos de seguridad y calidad;
   - orden ingestión -> comparación -> router;
   - presupuesto máximo y refinamiento único preservados;
   - rechazo de rutas no reconocidas.
9. Actualiza ADK_GRAPH_WORKFLOW_EVALUATION.md con una tabla "antes / prototipo
   / producción" y un diagrama Mermaid. Documenta que el prototipo no entra
   en producción hasta superar las pruebas y una revisión separada.
10. Ejecuta las pruebas pertinentes y reporta: archivos modificados, diagrama
    de aristas final, resultados de pruebas, incompatibilidades de API si las
    hubiera y cualquier decisión que deba validar una persona.

Límites y criterios de aceptación
- No cambies credenciales, variables de entorno, Terraform, IAM, IAP, Cloud
  Run, imágenes de contenedor, ni hagas deploy.
- No introduzcas dependencias nuevas sin justificarlo y sin verificar licencia
  y compatibilidad.
- No renombres contratos públicos ni rompas tests existentes.
- Detente y reporta si Workflow de ADK 2.12.0 no admite directamente un nodo
  requerido; propone un adaptador mínimo en vez de simular una integración.
- El resultado se acepta sólo si el prototipo es aislado, las pruebas pasan y
  las invariantes de seguridad se conservan de forma demostrable.
~~~
