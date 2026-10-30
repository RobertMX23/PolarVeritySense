# Alineación del flujo con Google ADK 2.x

**Versión verificada:** `google-adk 2.12.0`. Esta nota compara la
implementación con las páginas oficiales de ADK 2.x:
[colaboración](https://adk.dev/workflows/collaboration/),
[secuencia](https://adk.dev/agents/workflow-agents/sequential-agents/),
[bucle](https://adk.dev/agents/workflow-agents/loop-agents/),
[paralelo](https://adk.dev/agents/workflow-agents/parallel-agents/) y
[agentes personalizados](https://adk.dev/agents/custom-agents/).

## Comparación de patrones

| Patrón ADK | Ejemplo oficial | Implementación actual | Decisión |
|---|---|---|---|
| Colaboración | Un coordinador `LlmAgent` delega subagentes con modos `chat`, `task` o `single_turn`. | El coordinador no delega decisiones a un LLM: la ruta y el presupuesto se calculan con Python. | No adoptar modos de colaboración; mantienen el flujo libre de delegación implícita. |
| Secuencial | `SequentialAgent` ejecuta todos los subagentes en orden fijo y comparte el contexto. | Ingesta → comparación → despacho se ejecutan en ese orden, pero se detienen inmediatamente ante un caso bloqueado. | Mantener `GovernedWorkflowAgent` personalizado: el corte temprano es obligatorio. |
| Bucle | `LoopAgent` repite hasta una condición de salida o un máximo. | Sólo hay un refinamiento después de `REVISE`; nunca se vuelve a llamar al crítico. | No usar `LoopAgent`: un bucle permitiría más iteraciones de las autorizadas. |
| Paralelo | `ParallelAgent` ejecuta ramas independientes y exige coordinación explícita del estado. | Comparación depende de la telemetría y métricas de ingesta; analista, crítico y refinamiento dependen entre sí. | No usar `ParallelAgent`: introduciría carreras sobre el estado y el presupuesto. |
| Personalizado | Una subclase de `BaseAgent` implementa `_run_async_impl`, emite eventos y administra subagentes. | `GovernedWorkflowAgent`, `WorkflowRouteDispatcher`, preparación y etapas acotadas son `BaseAgent`. | Patrón principal; encaja con rutas condicionales, HITL y política de máximo tres llamadas. |

ADK indica que los workflows de plantilla han sido reemplazados en ADK 2.x por
estructuras de grafo y workflows dinámicos. El proyecto usa el equivalente
necesario: un grafo explícito y determinista dentro de agentes personalizados,
sin transferencias automáticas de un LLM.

## Matriz cruzada de mejoras

| Diferencia detectada | Riesgo o efecto | Ajuste aplicado | Verificación |
|---|---|---|---|
| El despachador escribía directamente en `ctx.session.state` antes de emitir el evento. | Estado menos observable y fuera del flujo de eventos ADK. | El despachador publica únicamente `EventActions(state_delta=...)`. | Las pruebas de rutas verifican que la decisión llega a la rama elegida. |
| Los eventos de los agentes personalizados no conservaban siempre `ctx.branch`. | Las trazas podían perder la rama de ejecución. | Todos los eventos propios incluyen `branch=ctx.branch`. | Suite de workflow y trazas de ADK Web. |
| Los nodos personalizados tenían nombre pero no descripción explícita. | El grafo resulta menos legible para operadores. | Se añadieron descripciones de responsabilidad a cada nodo del flujo. | Grafo e inspección de agentes. |
| La dependencia declaraba `google-adk` sin versión. | Una actualización no controlada podía cambiar la API. | Se fijó `google-adk==2.12.0`, la versión comprobada en el entorno y Cloud Run. | Instalación reproducible y `pytest -q`. |

## Jerarquía vigente

```text
SportAssistantRoot (GovernedWorkflowAgent)
├── TelemetryIngestion (programático)
├── SessionComparisonPreparation (programático)
└── WorkflowRouteDispatcher (programático)
    ├── SafetyEscalationResponse (programático)
    ├── DataQualityReviewResponse (programático)
    └── RecommendationAndApproval (programático)
        ├── PhysiologyAnalystAgent (Vertex AI)
        ├── SafetyCriticAgent (Vertex AI)
        └── ProposalRefinementAgent (Vertex AI, sólo tras REVISE)
```

Hay diez nodos activos. Sólo tres consumen Vertex AI. La ruta de seguridad y
la de calidad terminan antes de contactar el modelo; la aprobación posterior
registra sólo una auditoría local simulada.
