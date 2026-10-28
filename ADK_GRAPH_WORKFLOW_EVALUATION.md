# Evaluación de Graph Workflows de ADK 2.x

**Fecha de revisión:** 2026-10-28
**Versión local:** google-adk 2.12.0
**Referencias oficiales:** [Graph Workflows](https://adk.dev/graphs/),
[Graph Routes](https://adk.dev/graphs/routes/) y
[Data Handling](https://adk.dev/graphs/data-handling/).

## Ejemplo de referencia guardado

El siguiente ejemplo, compartido para esta revisión, muestra un grafo lineal
que alterna un agente, una función y otro agente. Se conserva como referencia
de la sintaxis declarativa de ADK, no como código ejecutable del producto.

~~~python
from google.adk import Agent, Event, Workflow
from pydantic import BaseModel

city_generator_agent = Agent(
    name="city_generator_agent",
    model="gemini-flash-latest",
    instruction="Return the name of a random city. Return only the name.",
)


class CityTime(BaseModel):
    time_info: str
    city: str


def lookup_time_function(node_input: str):
    return CityTime(time_info="10:10 AM", city=node_input)


city_report_agent = Agent(
    name="city_report_agent",
    model="gemini-flash-latest",
    input_schema=CityTime,
    instruction="Report the current time for the city in the input.",
)


def completed_message_function(node_input: str):
    return Event(message=f"{node_input}\nWORKFLOW COMPLETED.")


root_agent = Workflow(
    name="root_agent",
    edges=[
        ("START", city_generator_agent, lookup_time_function,
         city_report_agent, completed_message_function)
    ],
)
~~~

El patrón de ruta condicional de ADK usa una función que devuelve
Event(route=...) y un diccionario de aristas que asigna cada valor de ruta a su
nodo destino.

~~~python
def router(node_input: str):
    return Event(route="RUN_TASK_B" if condition(node_input) else "RUN_TASK_C")


root_agent = Workflow(
    name="routing_workflow",
    edges=[
        ("START", task_a_node, router),
        (router, {
            "RUN_TASK_B": task_b_node,
            "RUN_TASK_C": task_c_node,
        }),
    ],
)
~~~

## Tabla cruzada: ADK Graph frente al agente actual

| Concepto de Graph Workflow | Implementación en PolarVeritySense | Equivalencia | Observación |
|---|---|---|---|
| Workflow con edges | GovernedWorkflowAgent recorre sub_agents y controla interrupciones. | Parcial | Es un workflow dinámico en Python, no un grafo declarativo de ADK. |
| Nodo de función | TelemetryIngestion y SessionComparisonPreparation ejecutan Python determinista. | Sí | Calculan y validan antes del modelo. |
| Nodo LLM | PhysiologyAnalystAgent, SafetyCriticAgent y ProposalRefinementAgent. | Sí | Se conectan a Vertex AI mediante un gateway acotado. |
| Nodo herramienta | analyze_exercise_tool usa Polar AccessLink; el cargador FIT usa funciones de infraestructura. | Sí | El acceso a telemetría está separado del modelo. |
| Router con Event(route=...) | WorkflowRouteDispatcher calcula workflow_decision y llama directamente a un destino. | Parcial | La ruta existe, pero no está expresada con edges de Workflow. |
| Ramas de respuesta | SafetyEscalationResponse, DataQualityReviewResponse y RecommendationAndApproval. | Sí | Sólo se ejecuta una rama por caso. |
| Datos entre nodos | EventActions(state_delta=...) y session.state. | Sí | Se usa estado de sesión porque la evidencia, presupuesto y HITL sobreviven varios eventos. |
| Output tipado entre aristas | Pydantic valida OutboundSummary, Proposal y Critique. | Parcial | Los contratos son tipados, pero viajan en estado y no como output de nodo de grafo. |
| Entrada humana | Comando de aprobación vinculado a case_id y proposal_id en una invocación posterior. | Sí | Es HITL explícito; no es un nodo Human Input declarativo. |
| Bucle y salida | Refinamiento permitido una sola vez tras REVISE. | Sí, por política | No se usa LoopAgent ni un ciclo de grafo para impedir una cuarta inferencia. |
| Paralelismo | No se usa. | Correcto | Ingesta, comparación, analista y crítico tienen dependencias de datos y presupuesto. |

## Diferencias y decisión de mejora

| Diferencia | Riesgo de migrar sin diseño adicional | Acción recomendada |
|---|---|---|
| La topología no usa Workflow(edges=...). | Podrían perderse el bloqueo temprano, la reserva previa de llamadas y la auditoría HITL. | Mantener el workflow dinámico actual como implementación de producción. |
| Las rutas no se muestran como aristas declarativas. | El grafo visual puede ser menos directo de leer. | Crear un prototipo aislado de Workflow para TelemetryIngestion → Comparison → Router, sin reemplazar el flujo desplegado. |
| Los datos de estado son amplios para una demo. | ADK aconseja no mover payloads grandes por estado. | Mantener la allowlist actual; las muestras FIT crudas siguen fuera del estado que recibe Gemini. |
| La aprobación humana es una segunda invocación. | Un nodo de entrada humana cambiaría el contrato de sesión y requeriría pruebas nuevas. | Conservar el comando de aprobación exacto mientras la auditoría siga siendo simulada. |

## Conclusión

El agente actual implementa el propósito de los grafos: mezcla código
determinista, rutas explícitas, nodos de modelo y una compuerta humana. La
diferencia es de representación: usa un workflow dinámico con BaseAgent en vez
de Workflow(edges=...). Esa elección protege el límite de tres llamadas y las
rutas de bloqueo actuales.

Una migración a grafo debe empezar como prototipo y conservar estas
invariantes: cero llamadas de modelo en rutas de seguridad/calidad, máximo tres
generaciones por caso, refinamiento único y aprobación ligada a la propuesta.

El prompt para construir ese prototipo de manera controlada está en
[`ADK_GRAPH_IMPLEMENTATION_PROMPT.md`](ADK_GRAPH_IMPLEMENTATION_PROMPT.md).
