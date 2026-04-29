# Fase 3: Análisis Conceptual

## AWS Lambda Durable Functions y el Modelo de Actores en Computación Serverless

> **Síntesis teórica para el artículo del taller WOSC 2026**

<div align="center">

![Status](https://img.shields.io/badge/Status-Borrador%20interno-orange)
![Version](https://img.shields.io/badge/Versión-2.0-blue)
![Date](https://img.shields.io/badge/Abril-2026-lightgrey)

</div>

---

**Autor:** Julio César Siguenas Pacheco
**Institución:** Universitat Rovira i Virgili
**Grupo:** Cloud and Distributed Systems Lab
**Supervisión científica:** Pedro García-López
**Fecha:** Abril 2026

---

## 📋 Sobre este documento

> [!NOTE]
> **Alcance del documento.** Este documento integra los **dos entregables** solicitados para la Fase 3 según la Tarea Inicial:
>
> 1. **Resumen de literatura** (Sección 1) que sintetiza las tres fuentes de referencia indicadas — Azure Durable Entities, Spenger et al. (2024), y ExCamera (Fouladi et al., 2017).
> 2. **Ensayo de análisis conceptual** (Secciones 2 a 4) que responde a las cuatro preguntas planteadas: alineación con el modelo de actores, comparación con sistemas relacionados, garantías de tolerancia a fallos, e implicaciones para el diseño de sistemas distribuidos.
>
> La Sección 3 conecta explícitamente la teoría con las implementaciones de las Fases 1 y 2.

> [!IMPORTANT]
> **Pendientes de validación con el director** *(reunión del 30 de abril de 2026)*
>
> | Punto | Descripción |
> |-------|-------------|
> | **(a)** | Confirmar la atribución de la supervisión: el director oficial de la tesis es **Pedro Castillo**; verificar si la mención a Pedro García-López como supervisor científico es correcta. |
> | **(b)** | Confirmar la atribución del grupo en la **Sección 1.3** sobre Crucial. |
> | **(c)** | Confirmar la interpretación de los nuevos ratios de coste obtenidos tras la **homologación de memoria** del 29 de abril (ver Argumento 3 en Sección 4). |

---

## 📑 Índice

- [1. Revisión de Literatura](#1-revisión-de-literatura)
  - [1.1 El modelo de actores clásico](#11-el-modelo-de-actores-clásico-hewitt-bishop-y-steiger-1973)
  - [1.2 Actores virtuales: Orleans](#12-actores-virtuales-orleans)
  - [1.3 Spenger et al. (2024): cinco dimensiones](#13-abstracciones-tipo-actor-en-serverless-spenger-et-al-2024)
  - [1.4 Azure Durable Entities](#14-azure-durable-entities-el-precedente-de-microsoft)
  - [1.5 ExCamera: paralelismo masivo](#15-excamera-orquestación-serverless-con-paralelismo-masivo)
- [2. Análisis Conceptual](#2-análisis-conceptual)
  - [2.1 Alineación con el modelo de actores](#21-alineación-con-el-modelo-de-actores)
  - [2.2 Tabla de propiedades actoriales](#22-evaluación-de-propiedades-actoriales)
  - [2.3 Comparación con sistemas relacionados](#23-comparación-con-sistemas-relacionados)
  - [2.4 Tolerancia a fallos: exactly-once vs at-least-once](#24-tolerancia-a-fallos-y-garantías-semánticas)
  - [2.5 Implicaciones para el diseño](#25-implicaciones-para-el-diseño-de-sistemas-distribuidos)
- [3. Conexión con la implementación](#3-conexión-con-la-implementación)
  - [3.1 Justificación del caso del contador](#31-justificación-del-caso-del-contador)
  - [3.2 Mapeo SDK ↔ Modelo de Actores](#32-mapeo-sdk-↔-modelo-de-actores)
- [4. Síntesis y argumentos estructurantes](#4-síntesis-y-argumentos-estructurantes)
- [Referencias](#referencias)

---

## 1. Revisión de Literatura

> Esta sección sintetiza los pilares teóricos que fundamentan el análisis: el modelo de actores clásico, los actores virtuales de Orleans, las abstracciones tipo actor en serverless según Spenger et al. (2024), Azure Durable Entities como precedente directo, y el sistema ExCamera como referencia en orquestación serverless con paralelismo masivo.

### 1.1 El modelo de actores clásico (Hewitt, Bishop y Steiger, 1973)

El modelo de actores fue introducido por **Hewitt, Bishop y Steiger en 1973** [[He73]](#he73) como un formalismo universal para la inteligencia artificial basado en computación concurrente. Define la **unidad primitiva de computación** como un actor con tres componentes:

- 📦 **Estado privado** — encapsulado, no observable desde fuera
- 🔧 **Comportamiento** — funciones que pueden ejecutarse al recibir mensajes
- 📬 **Mailbox** — buzón de mensajes entrantes

Los actores se comunican exclusivamente por **paso de mensajes asíncrono**, procesan mensajes **secuencialmente** uno a uno, y pueden **crear nuevos actores** dinámicamente. Tres propiedades canónicas caracterizan el modelo:

| Propiedad | Descripción |
|-----------|-------------|
| **Encapsulación total del estado** | El estado interno no es accesible directamente |
| **Transparencia de ubicación** | Los actores se referencian por identidad, no por localización |
| **Procesamiento secuencial** | Cada actor procesa un mensaje a la vez |

### 1.2 Actores virtuales: Orleans

**Orleans** [[Or11]](#or11), desarrollado por Microsoft Research, extiende el modelo de actores con el concepto de **actores virtuales** o *grains*. La diferencia clave respecto al modelo clásico es que un grain **siempre existe virtualmente**: no requiere ser instanciado explícitamente. El runtime de Orleans gestiona automáticamente:

- 🟢 **Activación** — cuando llega un mensaje a un grain inactivo, el runtime lo despierta
- 🔴 **Passivation** — cuando un grain está inactivo durante un tiempo, el runtime libera sus recursos
- 🌐 **Distribución** — los grains se distribuyen automáticamente entre nodos del clúster (silos)

Este modelo simplifica enormemente la programación de sistemas distribuidos con estado, eliminando la gestión explícita de creación, destrucción y localización de actores.

### 1.3 Abstracciones tipo actor en serverless: Spenger et al. (2024)

Spenger, Carbone y Haller (2024) [[Sp24]](#sp24) presentan la **primera revisión sistemática** de los modelos de programación tipo actor para computación serverless. El paper, publicado en *Active Object Languages: Current Research Trends* (Lecture Notes in Computer Science, vol. 14360), caracteriza un conjunto de sistemas según **cinco dimensiones** que adoptamos como marco analítico para todo este trabajo:

| # | Dimensión | Pregunta clave |
|---|-----------|----------------|
| 1️⃣ | **Gestión de estado** | ¿Cómo se persiste el estado del actor? ¿Quién es responsable de su mantenimiento? |
| 2️⃣ | **Paso de mensajes** | ¿Hay mensajes asíncronos directos? ¿Se requieren intermediarios? |
| 3️⃣ | **Composición** | ¿Cómo se combinan actores para construir flujos complejos? |
| 4️⃣ | **Tolerancia a fallos** | ¿At-most-once, at-least-once o exactly-once? ¿Qué mecanismos soportan la recuperación? |
| 5️⃣ | **Garantías de ordenamiento** | ¿FIFO estricto, orden causal, sin garantías? |

> [!TIP]
> **Hallazgo central del survey:** los sistemas serverless existentes —incluyendo AWS Lambda, Azure Functions y Google Cloud Functions en su forma estándar— soportan *pobremente* el modelo de actores. Las funciones Lambda clásicas son **sin estado** por diseño; el estado debe externalizarse a DynamoDB, S3 u otros almacenes.

Esto introduce acoplamiento explícito entre la lógica de negocio y la infraestructura de persistencia, contradice la encapsulación de actores, y exige que el programador gestione manualmente la serialización, los reintentos y la idempotencia.

El survey identifica varias iniciativas que intentan cerrar esta brecha:

- **Cloudburst** [[Sr20]](#sr20) — funciones serverless con estado mediante caché distribuida (Anna KVS) y protocolo de causalidad.
- **Crucial** [[Po22]](#po22) — del **Cloud and Distributed Systems Lab de la URV**, expone objetos Java de alto nivel sobre almacenamiento distribuido, permitiendo programar en serverless con abstracciones de memoria compartida.
- **Portals** (Spenger et al., 2022) — unifica el modelo de dataflow con actores para flujos de trabajo serverless con estado.

> [!WARNING]
> Ninguno de estos sistemas está integrado nativamente en el runtime de un proveedor cloud de primer nivel.

### 1.4 Azure Durable Entities: el precedente de Microsoft

**Azure Durable Entities** [[Mi26]](#mi26), introducidas en Azure Durable Functions v2 (2019), constituyen el **antecedente directo más relevante** de AWS Lambda Durable Functions. Están inspiradas en Orleans y exponen explícitamente una abstracción tipo actor: cada entidad tiene una identidad única (`EntityId`), mantiene estado interno persistente, y procesa operaciones secuencialmente para prevenir condiciones de carrera.

> *"Durable entities are similar to virtual actors, also called grains, from the Orleans project. You address durable entities by using an entity ID. Durable entity operations run serially to prevent race conditions."*
> — Microsoft Learn, Azure Durable Functions: Durable Entities (2026)

Las **tres primitivas** que ofrece el modelo son:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. OPERACIONES sobre entidades                                 │
│     • Invocaciones síncronas que leen/modifican estado interno  │
│     • Devuelven un resultado al llamador                        │
│                                                                 │
│  2. SEÑALIZACIÓN entre entidades  (signal)                      │
│     • Mensajes asíncronos sin esperar respuesta                 │
│     • Aporta verdadera mensajería actor-a-actor                 │
│                                                                 │
│  3. BLOQUEOS Y ORQUESTACIONES CRÍTICAS  (lock)                  │
│     • Coordinación de múltiples entidades en transacciones      │
│     • Protocolo de adquisición ordenada para evitar deadlocks   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Diferencias respecto a Orleans:**

| Aspecto | Orleans | Azure Durable Entities |
|---------|---------|------------------------|
| **Prioridad** | Baja latencia | Durabilidad |
| **Ubicación del estado** | Memoria del silo | Azure Storage Tables |
| **Latencia de operación** | μs–ms | 100–500 ms (round-trip) |
| **Garantías de mensajería** | No para todos los grains | Ordenada y confiable |
| **Bloqueo distribuido** | ❌ No nativo | ✅ Soportado |

### 1.5 ExCamera: orquestación serverless con paralelismo masivo

El sistema **ExCamera** [[Fo17]](#fo17), publicado en NSDI 2017, es una **referencia académica clave** para entender el límite del paralelismo en serverless con estado. ExCamera implementa un sistema de codificación de vídeo H.264 que ejecuta **miles de funciones Lambda concurrentes** —hasta 4.000 simultáneamente— para procesar vídeo en tiempo casi real.

Su contribución central no es el dominio del vídeo en sí, sino el **mecanismo de coordinación** que permite a tantas funciones efímeras compartir información sobre estado intermedio del trabajo.

**Tres aspectos directamente relevantes** para nuestro análisis de las durable functions:

#### 🗂️ Coordinación mediante registro de estado en S3
Cada función Lambda escribe sus resultados intermedios y su estado de progreso en un objeto S3 estructurado. Otras funciones pueden leer este registro para conocer qué partes del trabajo ya están terminadas, qué chunks aún están en proceso, y qué dependencias deben esperarse.

> Este mecanismo es funcionalmente equivalente al checkpoint de las durable functions, pero **gestionado explícitamente por la aplicación** en vez de internalizado en el SDK.

#### 🔌 Comunicación entre Lambdas mediante "rendezvous server"
Para casos donde el modelo basado en S3 introduce demasiada latencia, ExCamera utiliza un **servidor intermediario en EC2** que coordina la comunicación bidireccional entre Lambdas.

> Esta solución es exactamente lo que las durable functions evitan al integrar la coordinación nativamente en el runtime de Lambda — pero también es exactamente lo que las durable functions todavía **no soportan** en su versión actual, porque carecen de mensajería entre ejecuciones.

#### ⚖️ Demostración empírica del trade-off paralelismo vs estado
ExCamera demuestra que es posible coordinar miles de funciones Lambda sin estado para una tarea con dependencias complejas, **pero al precio de una infraestructura externa de coordinación significativa**. Las durable functions ofrecen el extremo opuesto: coordinación sencilla y nativa, pero solo dentro de una única ejecución secuencial.

> [!IMPORTANT]
> **Conexión directa con nuestro trabajo de Fase 2:** la Fase 2 implementa un pipeline de codificación de vídeo conceptualmente similar al de ExCamera, pero usando durable functions. Nuestros resultados muestran que la primitiva `context.parallel()` no es funcional en el SDK Python v12-v13, lo que reduce el pipeline a ejecución secuencial.
>
> Esto significa que las durable functions, en su versión actual, **no pueden replicar el modelo ExCamera** de paralelismo masivo: ofrecen las garantías de durabilidad y replay automático, pero pierden el paralelismo que ExCamera demostró posible.

---

## 2. Análisis Conceptual

> Esta sección responde a las cuatro preguntas planteadas en la Tarea Inicial: alineación con el modelo de actores, comparación con sistemas relacionados, garantías de tolerancia a fallos, e implicaciones para el diseño.

### 2.1 Alineación con el modelo de actores

Aplicando las propiedades canónicas del modelo de actores de Hewitt et al. (1973), las durable functions **satisfacen parcialmente el paradigma**.

#### ✅ Satisfacen tres propiedades centrales

- **Identidad única** — el `execution_name` es una dirección persistente que garantiza idempotencia.
- **Procesamiento secuencial** — los pasos se ejecutan uno a uno, sin condiciones de carrera.
- **Tolerancia a fallos** — el runtime gestiona reintentos con backoff exponencial y checkpoint-and-replay de forma transparente.

#### ❌ Carecen de dos propiedades fundamentales

- **Paso de mensajes actor-actor** — no existe mensajería directa entre ejecuciones durables, a diferencia de Orleans.
- **Creación dinámica de actores** — una ejecución no puede invocar a otra como sub-actor en tiempo de ejecución.

> [!NOTE]
> En la taxonomía de Spenger et al. (2024), estas limitaciones sitúan a AWS Lambda Durable Functions como un **sistema de orquestación de actores fiable**: cobertura completa en gestión de estado, tolerancia a fallos y ordenamiento, pero sin paso de mensajes ni composición dinámica.

### 2.2 Evaluación de propiedades actoriales

| Propiedad | AWS Lambda Durable Functions | Evaluación |
|-----------|------------------------------|------------|
| **Identidad única** | `execution_name` actúa como dirección persistente | ✅ Satisfecha |
| **Encapsulación del estado** | Estado serializado y persistido en checkpoint store interno | ✅ Satisfecha |
| **Procesamiento secuencial** | Pasos ejecutados secuencialmente, replay determinista | ✅ Satisfecha |
| **Mensajería actor-actor** | Sin primitiva de mensajería entre ejecuciones durables | ❌ Ausente |
| **Creación dinámica de actores** | No es posible invocar otra ejecución durable como sub-actor | ❌ Ausente |
| **Tolerancia a fallos** | Reintentos automáticos, checkpoint-and-replay nativo | ✅ Satisfecha |
| **Existencia virtual** | Sin activación/passivation automática (la ejecución tiene ciclo de vida acotado) | ⚠️ Parcial |

### 2.3 Comparación con sistemas relacionados

| Sistema | Gestión de estado | Mensajería actor | Tolerancia a fallos | Latencia | Despliegue |
|---------|-------------------|------------------|---------------------|----------|------------|
| **Akka (JVM)** | En memoria | ✅ Nativa async | Jerarquías de supervisión | μs | Servidor dedicado |
| **Orleans (MS)** | Virtual + pluggable | ✅ At-most-once | Reactivación de silo | ms (warm) | Clústeres en nube |
| **Azure Durable Entities** | Durable (Storage) | ✅ Señalización | At-least-once | 100–500 ms | Serverless (Azure) |
| **Temporal** | Durable (log) | ⚠️ Señales externas | At-least-once | 100–300 ms | Servidor / SaaS |
| **Cloudburst** | Caché (Anna KVS) | ✅ Causalidad | A nivel de caché | <1 ms | Investigación (Lambda) |
| **Crucial (URV)** | Objetos distribuidos | ⚠️ Indirecta (memoria compartida) | A nivel de almacén | ~10–50 ms | Investigación (Lambda) |
| **AWS Lambda DF** *(este trabajo)* | Checkpoint del SDK | ❌ Ausente | Retry + replay | 596–9.300 ms (+ cold 746–1.474 ms) | Serverless nativo |

**Leyenda:** ✅ Satisfecho • ⚠️ Parcial • ❌ Ausente

### 2.4 Tolerancia a fallos y garantías semánticas

Una de las contribuciones conceptuales de este análisis es **distinguir con precisión** las garantías ofrecidas por las durable functions:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   GARANTÍA EFECTIVA DE LAS DURABLE FUNCTIONS                        │
│                                                                     │
│   ┌─────────────────────────────────┐                               │
│   │  EXACTLY-ONCE para resultados   │ ← El resultado de un paso     │
│   │                                 │   completado se cachea y      │
│   │  (semántica observable)         │   nunca se re-ejecuta         │
│   └─────────────────────────────────┘                               │
│                                                                     │
│                  ┌─── coexiste con ───┐                             │
│                                                                     │
│   ┌─────────────────────────────────┐                               │
│   │  AT-LEAST-ONCE para ejecución   │ ← Un paso puede ejecutarse    │
│   │                                 │   múltiples veces si falla    │
│   │  (semántica subyacente)         │   antes de checkpointar       │
│   └─────────────────────────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Implicación práctica:** los efectos secundarios externos (escrituras a APIs, bases de datos, sistemas de mensajería) **no son automáticamente idempotentes**. La responsabilidad de garantizar idempotencia ante reintentos sigue siendo del programador, reduciendo la garantía efectiva a *at-least-once* para efectos externos.

### 2.5 Implicaciones para el diseño de sistemas distribuidos

Las durable functions habilitan **patrones de diseño** que antes requerían infraestructura dedicada:

- 🤖 **Pipelines de agentes de IA** — flujos multi-paso con estado entre invocaciones de modelos
- 🔄 **ETL recuperables** — procesos de extracción/transformación que sobreviven a fallos sin reiniciar desde cero
- 👤 **Flujos human-in-the-loop** — vía `context.wait_for_event()` para esperar input humano
- 💼 **Sagas de microservicios** — sin necesidad de base de datos de estado separada

---

## 3. Conexión con la implementación

> Esta sección conecta los conceptos teóricos con las implementaciones concretas de las Fases 1 y 2, atendiendo al deliverable 3.3 de la Tarea Inicial.

### 3.1 Justificación del caso del contador

La Fase 1 implementa un **contador con estado** como caso canónico para evaluar las primitivas básicas. Esta elección no es arbitraria: el contador es el ejemplo de actor más simple y mejor estudiado en la literatura del modelo de actores desde Agha (1985), y aparece como caso introductorio en Spenger et al. (2024) y en la documentación oficial de Orleans y Azure Durable Entities.

> [!NOTE]
> **Autocrítica honesta:** el contador implementado en Fase 1 **no es estrictamente un actor clásico**. Un actor mantiene estado entre invocaciones independientes (Orleans, Akka), mientras que nuestra implementación durable inicializa el estado al comenzar cada ejecución. Lo que sí demuestra Fase 1 son las **primitivas de checkpoint, replay y tolerancia a fallos**, que son los componentes actoriales presentes en el SDK.

### 3.2 Mapeo SDK ↔ Modelo de Actores

Esta tabla cruza las primitivas del SDK de AWS Lambda Durable Functions con los conceptos del modelo de actores, citando **evidencia empírica** de los runs de Fase 1 y Fase 2:

| Primitiva SDK | Concepto actor | Evidencia empírica |
|---------------|----------------|---------------------|
| `@durable_execution` | Definición de actor (clase) | Fase 1: contador implementado como entidad con identidad |
| `@durable_step` | Comportamiento del actor (método) | `initialize_counter`, `apply_counter_operation`, `build_response` |
| `context.step()` | Invocación de método sobre actor | Cada paso se persiste tras completarse |
| `execution_name` | Identidad del actor (dirección persistente) | `counter_idempotency_001` reutiliza nombre, evita re-ejecución |
| Checkpoint store | Encapsulación del estado | Fase 1: 0,025 KB persistente entre invocaciones |
| Retry automático con backoff | Tolerancia a fallos del actor | `vid_enc_fail_once_001`: reintento exitoso tras fallo transitorio |
| Replay desde checkpoint | Recuperación tras fallo | `counter_replay_observation_001`: pasos completados nunca re-ejecutados |
| `context.parallel()` | Creación dinámica de sub-actores | ❌ No funcional en SDK v12–v13 (SerDesError) |
| Mensajería entre ejecuciones | Paso de mensajes actor-actor | ❌ Ausente del SDK actual |

---

## 4. Síntesis y argumentos estructurantes

A partir del análisis anterior, identificamos **cuatro argumentos estructurantes** que sintetizan la contribución de este trabajo a la comunidad de investigación serverless:

### 🔹 Argumento 1 — Viejo paradigma, nuevas primitivas

AWS Lambda Durable Functions **no introduce un paradigma nuevo**. El modelo checkpoint-and-replay fue formalizado por Burckhardt et al. (2021) en el contexto de Azure Durable Functions, y el modelo de actores tiene 50 años de historia desde Hewitt et al. (1973). Lo que sí aporta AWS es **la integración nativa de estas primitivas en un proveedor cloud de primer nivel (tier-1)**, eliminando la necesidad de infraestructura adicional. Esta es la contribución principal del servicio: no inventar, sino **democratizar el acceso** a un paradigma maduro.

### 🔹 Argumento 2 — La restricción del paralelismo es sistémica

La no funcionalidad de `context.parallel()` en el SDK Python v12–v13 **no es un bug menor**. Refleja una limitación arquitectónica profunda: serializar callables Python para distribuirlos a sub-ejecuciones requiere un protocolo padre-hijo que el SDK actual no implementa. Esto significa que las durable functions **no pueden replicar el modelo ExCamera** de paralelismo masivo. El servicio se sitúa en el extremo opuesto del espectro: máxima simplicidad de coordinación, mínimo paralelismo intra-ejecución.

### 🔹 Argumento 3 — El coste de la durabilidad

El sobrecoste de **16–19×** que observamos respecto al enfoque tradicional (a igualdad de configuración de memoria, ambas funciones a 128 MB) refleja el **precio de las garantías actoriales**: serialización de estado, persistencia de checkpoint, y múltiples invocaciones Lambda internas. El coste tradicional, dominado por las operaciones DynamoDB del envoltorio manual de estado, es desproporcionadamente bajo en compute, lo que amplifica el ratio. Azure Durable Entities incurre en costes similares. Orleans, al mantener el estado en memoria, evita este coste — pero requiere silos dedicados con coste de infraestructura fijo. Para la comunidad de investigación serverless, este trade-off es una **contribución de medición original**.

> [!WARNING]
> Estos ratios provienen de la re-ejecución del 29 de abril de 2026 con memoria homologada a 128 MB en ambas funciones. La interpretación de los nuevos ratios queda **pendiente de validación con el director**.

### 🔹 Argumento 4 — Posicionamiento taxonómico

En la taxonomía de Spenger et al. (2024), AWS Lambda Durable Functions ocupa una **posición específica y novedosa**:

```
                    ALTA composición                ALTA mensajería
                    BAJA durabilidad                BAJA durabilidad
                          │                              │
                          │                              │
      Orleans ────────────┤                              ├──────────── Akka
                          │                              │
                          │      ┌──────────────┐        │
                          │      │   AWS LDF    │        │
                          │      │ (este trabajo)│       │
                          │      └──────────────┘        │
                          │                              │
                          │       Azure Durable          │
                          │         Entities             │
                          │                              │
                    BAJA composición                BAJA mensajería
                    ALTA durabilidad                ALTA durabilidad
```

AWS Lambda DF se sitúa en el **cuadrante de alta durabilidad y composición secuencial fiable, pero sin mensajería actor-actor**. Esta posición no estaba previamente ocupada por ningún sistema de proveedor de primer nivel.

---

## Referencias

<a id="he73"></a>**[He73]** Hewitt, C., Bishop, P., y Steiger, R. (1973). A Universal Modular ACTOR Formalism for Artificial Intelligence. En *IJCAI '73*, pp. 235–245.

<a id="or11"></a>**[Or11]** Bykov, S., Geller, A., Kliot, G., Larus, J. R., Pandya, R., y Thelin, J. (2011). Orleans: Cloud Computing for Everyone. En *SOCC '11*, ACM. doi:10.1145/2038916.2038932.

<a id="sp24"></a>**[Sp24]** Spenger, J., Carbone, P., y Haller, P. (2024). A Survey of Actor-Like Programming Models for Serverless Computing. En *Active Object Languages: Current Research Trends*, Lecture Notes in Computer Science, vol. 14360, pp. 123–146. Springer, Cham. doi:10.1007/978-3-031-51060-1_5.

<a id="mi26"></a>**[Mi26]** Microsoft Learn. (2026). Durable entities — Azure Functions. Disponible en: https://learn.microsoft.com/azure/azure-functions/durable/durable-functions-entities

<a id="fo17"></a>**[Fo17]** Fouladi, S., Wahby, R. S., Shacklett, B., Balasubramaniam, K., Zeng, W., Bhalerao, R., Sivaraman, A., Barrett, G., y Winstein, K. (2017). Encoding, Fast and Slow: Low-Latency Video Processing Using Thousands of Tiny Threads. En *NSDI '17*, USENIX Association.

<a id="bu21"></a>**[Bu21]** Burckhardt, S., Gillum, C., Justo, D., Kallas, K., McMahon, C., y Meiklejohn, C. S. (2021). Durable Functions: Semantics for Stateful Serverless. *Proc. ACM Program. Lang.*, 5(OOPSLA), Article 133. doi:10.1145/3485510.

<a id="po22"></a>**[Po22]** Barcelona Pons, D., Sutra, P., Sánchez-Artigas, M., París, G., y García-López, P. (2022). Stateful Serverless Computing with Crucial. *ACM Trans. Softw. Eng. Methodol.*, 31(3):39:1–39:38. doi:10.1145/3490386.

<a id="sr20"></a>**[Sr20]** Sreekanti, V., Wu, C., Lin, X. C., Schleier-Smith, J., Gonzalez, J. E., Hellerstein, J. M., y Tumanov, A. (2020). Cloudburst: Stateful Functions-as-a-Service. *Proc. VLDB Endow.*, 13(11):2438–2452.

<a id="zh21"></a>**[Zh21]** Zhang, H., Cardoza, A., Chen, P. B., Angel, S., y Liu, V. (2021). Fault-Tolerant and Transactional Stateful Serverless Workflows. En *OSDI '21*, USENIX Association.

<a id="aws25"></a>**[AWS25]** Amazon Web Services. (2025, 2 de diciembre). Build multi-step applications and AI workflows with AWS Lambda Durable Functions. *AWS Blog*. Disponible en: https://aws.amazon.com/blogs/aws/build-multi-step-applications-and-ai-workflows-with-aws-lambda-durable-functions/

---

<div align="center">

*Documento de trabajo · Provisional · Sujeto a revisión tras la reunión con el director*

**Repositorio:** [`jcsp-research/aws-durable-functions-research`](https://github.com/jcsp-research/aws-durable-functions-research)

</div>
