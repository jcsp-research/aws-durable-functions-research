# Fase 3: Análisis Conceptual — AWS Lambda Durable Functions — y el Modelo de Actores en Computación Serverless

*Síntesis teórica para el artículo de taller WOSC 2026*

**Julio César Siguenas Pacheco · Universitat Rovira i Virgili · Grupo Cloud and Distributed Systems Lab · Supervisado por: Marc Sánchez-Artigas · Abril 2026**

---

## 1. Revisión de Literatura

Esta sección sintetiza los tres pilares teóricos que fundamentan el análisis: el modelo de actores clásico, los actores virtuales de Orleans, y las abstracciones tipo actor en serverless según Spenger et al. (2024).

### 1.1 El modelo de actores clásico: Hewitt, 1973

El modelo de actores fue propuesto originalmente por Hewitt, Bishop y Steiger en 1973 como un formalismo universal para la computación concurrente. En este modelo, un *actor* es la unidad primitiva de computación: encapsula estado privado, comportamiento y una dirección de correo (mailbox). Los actores se comunican exclusivamente mediante paso de mensajes asíncrono; nunca comparten memoria. Cuando un actor recibe un mensaje, puede: (1) enviar mensajes a otros actores, (2) crear nuevos actores, y (3) designar el comportamiento que usará para el próximo mensaje recibido. Esta última propiedad constituye la base del manejo de estado mutable en el modelo clásico.

Tres propiedades fundamentales distinguen el modelo de actores de otros paradigmas de concurrencia. Primero, el **no determinismo justo**: el orden de entrega de mensajes entre actores distintos no está garantizado, pero un actor dado procesa sus mensajes secuencialmente. Segundo, la **transparencia de ubicación**: un actor es contactado por su dirección, no por su localización física. Tercero, la **encapsulación total**: ningún agente externo puede inspeccionar o modificar el estado interno de un actor directamente.

### 1.2 Actores virtuales: el modelo Orleans (Microsoft Research)

El proyecto Orleans, desarrollado en Microsoft Research para soportar los servicios en la nube del videojuego Halo, introdujo la abstracción de *actores virtuales* (denominados *grains*). La distinción fundamental respecto al modelo clásico es que un actor virtual *siempre existe* — no puede ser creado ni destruido explícitamente. Su existencia es conceptualmente eterna; el runtime gestiona automáticamente su activación en memoria cuando recibe un mensaje y su *passivation* (descarga de memoria) cuando está inactivo. Esta semántica simplifica radicalmente el ciclo de vida del actor para el programador.

Orleans proporciona tres garantías clave que lo diferencian de los actores clásicos: (1) **activación automática** — un mensaje a un grain inactivo lo instancia automáticamente en un silo disponible; (2) **at-most-once delivery** — Orleans no garantiza la entrega de mensajes entre grains en caso de fallo del silo, a diferencia de sistemas con colas duraderas; y (3) **transparencia de distribución** — el programador ignora en qué silo reside un grain en cada momento.

### 1.3 Abstracciones tipo actor en serverless: Spenger et al., 2024

Spenger, Carbone y Haller (2024) presentan la primera revisión sistemática de los modelos de programación tipo actor para computación serverless. El paper, publicado en *Active Object Languages: Current Research Trends* (Lecture Notes in Computer Science, vol. 14360), caracteriza un conjunto de sistemas según cinco dimensiones: (1) gestión de estado, (2) paso de mensajes, (3) composición, (4) tolerancia a fallos, y (5) garantías de ordenamiento.

Un hallazgo central del survey es que los sistemas serverless existentes — incluyendo AWS Lambda, Azure Functions y Google Cloud Functions en su forma estándar — soportan *pobremente* el modelo de actores. Las funciones Lambda clásicas son sin estado por diseño; el estado debe externalizarse a DynamoDB, S3 u otros almacenes. Esto introduce acoplamiento explícito entre la lógica de negocio y la infraestructura de persistencia, contradice la encapsulación de actores, y exige que el programador gestione manualmente la serialización, los reintentos y la idempotencia.

El survey identifica varias iniciativas que intentan cerrar esta brecha. **Cloudburst** (Sreekanti et al., 2020) ofrece funciones serverless con estado mediante un sistema de caché distribuida (Anna KVS) y un protocolo de causalidad. **Crucial** (Pons et al., 2022, del grupo de Marc Sánchez-Artigas en URV) expone objetos Java de alto nivel sobre almacenamiento distribuido, permitiendo programar en serverless con abstracciones de memoria compartida. **Portals** (Spenger et al., 2022) unifica el modelo de dataflow con actores para flujos de trabajo serverless con estado. Ninguno de estos sistemas, sin embargo, está integrado nativamente en el runtime de un proveedor cloud de primer nivel.

### 1.4 Azure Durable Entities: el precedente de Microsoft

Azure Durable Entities, introducidas en Azure Durable Functions v2 (2019), constituyen el antecedente directo más relevante de AWS Lambda Durable Functions. Están inspiradas en Orleans y exponen explícitamente una abstracción tipo actor: cada entidad tiene una identidad única (`EntityId`), mantiene estado interno persistente, y procesa operaciones secuencialmente para prevenir condiciones de carrera. La documentación oficial de Microsoft reconoce explícitamente:

> "Durable entities are similar to virtual actors, also called grains, from the Orleans project. You address durable entities by using an entity ID. Durable entity operations run serially to prevent race conditions." — Microsoft Learn, Azure Durable Functions: Durable Entities (2026)

Sin embargo, existen diferencias importantes respecto a Orleans. Azure Durable Entities priorizan **durabilidad sobre latencia**: el estado se persiste en Azure Storage Tables tras cada operación, lo que introduce una latencia de round-trip a almacenamiento externo que Orleans (con estado en memoria dentro del silo) evita. A cambio, Durable Entities ofrecen garantías de entrega de mensajes ordenada y confiable — algo que Orleans no garantiza para todos los mensajes entre grains. Adicionalmente, Azure Durable Entities soportan **bloqueo distribuido** mediante orquestaciones, lo que permite coordinar múltiples entidades en transacciones, una capacidad ausente en el modelo de actores clásico.

## 2. Análisis Conceptual: AWS Lambda Durable Functions y el Modelo de Actores

### 2.1 ¿Son actores las AWS Lambda Durable Functions?

Esta pregunta es central para el posicionamiento del paper. La respuesta es: **parcialmente sí, con diferencias estructurales significativas**. Aplicando las cinco propiedades canónicas del modelo de actores como criterio de análisis, la Tabla 1 muestra el grado de alineación.

**Tabla 1: Alineación de AWS Lambda Durable Functions con las propiedades del modelo de actores clásico.**

| Propiedad del actor | AWS Lambda Durable Functions | Valoración |
| --- | --- | --- |
| **Identidad única**; (Cada actor tiene una dirección persistente) | Cada ejecución durable tiene un `execution_name` único y persistente. Re-invocar con el mismo nombre devuelve el resultado cacheado sin re-ejecutar pasos. | ✅ Satisfecho |
| **Encapsulación de estado**; (Estado privado, no compartido) | El estado del checkpoint es gestionado internamente por el SDK; la aplicación no accede al almacén de checkpoints directamente. Sin embargo, el estado de la aplicación se pasa explícitamente entre pasos como parámetros. | ⚠️ Parcial |
| **Procesamiento secuencial**; (Un mensaje a la vez, sin concurrencia interna) | Los pasos se ejecutan secuencialmente por diseño del SDK. No hay ejecución concurrente dentro de una misma ejecución durable (y las primitivas paralelas no son funcionales en Python, según §5 del paper). | ✅ Satisfecho (secuencial) |
| **Paso de mensajes asíncrono**; (Comunicación exclusivamente por mensajes) | No existe mensajería entre ejecuciones durables. Cada ejecución es un flujo independiente disparado por un evento externo. No hay primitivas para que una ejecución durable envíe mensajes a otra. | ❌ Ausente |
| **Creación dinámica de actores**; (Un actor puede crear otros actores) | No está soportado. Una ejecución durable no puede invocar otra ejecución durable como sub-actor. La orquestación de múltiples ejecuciones requiere lógica externa (Step Functions, EventBridge). | ❌ Ausente |
| **Tolerancia a fallos**; (Aislamiento y recuperación ante fallos) | Retry automático con backoff exponencial observado: 10s→12s→23s→60s→87s. Pasos completados nunca se re-ejecutan (checkpoint-and-replay confirmado empíricamente en §3.5 del paper). Error propagado como `CallableRuntimeError` tras 6 intentos. | ✅ Satisfecho |
| **Existencia virtual**; (El actor "siempre existe" (Orleans)) | Parcial: el execution_name persiste durante el período de retención (14 días por defecto). Fuera de ese período, la ejecución se elimina. No es eterna como los grains de Orleans. | ⚠️ Parcial |

El análisis revela una conclusión importante: AWS Lambda Durable Functions satisfacen las propiedades de *workflow engine* del modelo de actores (identidad, secuencialidad, tolerancia a fallos) pero carecen de las propiedades de *comunicación entre actores* (mensajería actor-a-actor, jerarquías de supervisión, creación dinámica). En la taxonomía de Spenger et al. (2024), esto las sitúa más cerca de los *reliable actor frameworks* orientados a orquestación (como Azure Durable Orchestrations o Temporal) que de los sistemas de actores de propósito general (como Akka o Orleans).

### 2.2 Mapeo de primitivas SDK a operaciones de actores

La Tabla 2 establece la correspondencia entre las primitivas del SDK de AWS Lambda Durable Functions y las operaciones fundamentales del modelo de actores, enriquecida con evidencia empírica de nuestros experimentos.

**Tabla 2: Correspondencia entre primitivas SDK y operaciones del modelo de actores.**

| Primitiva SDK | Operación de actor equivalente | Evidencia empírica |
| --- | --- | --- |
| `@durable_step` + `context.step()` | Procesamiento de un mensaje con actualización de estado. El resultado se persiste como un evento en el log del actor. | Fase 1: 3 pasos secuenciales (initialize_counter, apply_counter_operation, build_response). Cada uno genera StepStarted/StepSucceeded en el historial. |
| `execution_name` | Dirección del actor. Permite idempotencia: re-invocar con la misma dirección devuelve el estado cacheado. | Fase 1 (counter_idempotency_001): resultado counter_value=1 idéntico en ambas invocaciones. Fase 2 (replay): version=3 inmutable tras re-invocación. |
| Checkpoint-and-replay automático | Persistencia del estado del actor tras cada mensaje procesado. El replay garantiza que el actor reanuda desde su último estado conocido. | Fase 1 (counter_replay_observation_001): initialize_counter aparece una sola vez en 16 eventos de historial. apply_counter_operation es reintentada repetidamente sin re-ejecutar el paso anterior. |
| Retry con backoff exponencial | Supervisión del actor por el runtime. Los fallos son aislados y gestionados por la infraestructura, no por el programador. | Fase 1 (counter_fail_always_001): 6 intentos, backoff 10→12→23→60→87s. Fase 2 (vid_enc_fail_once_001): reintento automático sin código adicional de aplicación. |
| `context.parallel()` / `context.map()` | Fork de actores hijo para trabajo concurrente. *No funcional en Python SDK v12–v13.* | Fase 2: SerDesError al serializar callables. actual_parallel_chunks=1 en todos los experimentos. Fallback a ejecución secuencial. |
| `context.wait_for_event()` | Suspensión del actor esperando un mensaje externo. Permite callbacks y aprobaciones humanas (human-in-the-loop). | No evaluado en este trabajo. Señalado como trabajo futuro relevante para flujos de agentes de IA. |

### 2.3 Comparación con sistemas relacionados

La Tabla 3 posiciona AWS Lambda Durable Functions en el panorama de sistemas tipo actor, cubriendo las dimensiones identificadas por Spenger et al. (2024) enriquecidas con nuestra evaluación empírica.

**Tabla 3: Comparación de sistemas tipo actor en computación distribuida/serverless.**

| Sistema | Modelo de estado | Mensajería actor-actor | Tolerancia a fallos | Latencia | Contexto de despliegue |
| --- | --- | --- | --- | --- | --- |
| **Akka (JVM)** | En memoria, explícito | ✅ Nativa, asíncrona | Jerarquías de supervisión | Microsegundos | Servidor dedicado |
| **Orleans (Microsoft)** | Virtual, en memoria + persistencia pluggable | ✅ Nativa (at-most-once) | Reactivación automática en otro silo | Milisegundos (warm) | Clusters en la nube |
| **Azure Durable Entities** | Durable, en Azure Storage Tables | ✅ Señalización entre entidades | At-least-once, bloqueo distribuido | ~100–500 ms/operación | Serverless (Azure Functions) |
| **Temporal / Conductor** | Durable (event log) | ⚠️ Mediante señales externas | At-least-once, replay exacto | ~100–300 ms/paso | Servidor dedicado / SaaS |
| **Cloudburst (investigación)** | Caché distribuida (Anna KVS) | ✅ Causalidad explícita | A nivel de caché | Sub-milisegundo (caché) | Investigación (Lambda) |
| **Crucial (investigación, URV)** | Objetos Java distribuidos | ⚠️ Indirecta (memoria compartida) | A nivel de almacén | ~10–50 ms | Investigación (Lambda) |
| **AWS Lambda Durable Functions** (este trabajo) | Checkpoint SDK interno (0.025–5.2 KB observado) | ❌ No soportada | Retry + backoff (10→87s), checkpoint-and-replay | 630–9,200 ms/ejecución (+cold start 570–1,384 ms) | Serverless nativo (AWS Lambda) |

La comparación revela una posición singular de AWS Lambda Durable Functions: es el primer sistema de ejecución durable integrado nativamente en un runtime Lambda de primer proveedor (junto con Azure Durable Functions en el ecosistema Microsoft). A diferencia de Temporal o Conductor, no requiere infraestructura de orquestación dedicada. A diferencia de Cloudburst o Crucial, no es un sistema académico sino un servicio en producción. Sin embargo, a diferencia de Azure Durable Entities, carece de mensajería entre ejecuciones y de jerarquías de supervisión, lo que limita su expresividad como sistema de actores completo.

### 2.4 Garantías de tolerancia a fallos: exactamente una vez vs. al menos una vez

La semántica de tolerancia a fallos es una dimensión crítica para la defensa de la tesis. Las durable functions de AWS ofrecen lo que denominamos **exactly-once semántics for step results** combinado con **at-least-once execution semantics**. Esta distinción es sutil pero importante para la investigación.

El modelo funciona así: un paso puede ser ejecutado más de una vez (at-least-once), pero su resultado solo se registra una vez en el checkpoint (exactly-once para el resultado). Una vez que un paso ha producido un resultado exitoso y este ha sido checkpointed, cualquier re-invocación de la ejecución durable reproduce ese resultado desde el checkpoint sin re-ejecutar el paso. Esto es lo que observamos empíricamente en la Fase 1 (`counter_replay_observation_001`): `initialize_counter` aparece exactamente una vez en el historial de 16 eventos, a pesar de que la Lambda fue re-invocada múltiples veces por el runtime.

Esta semántica es equivalente al modelo de **event sourcing con replay determinista** descrito por Gillum et al. (2023) para Azure Durable Functions. La condición para que sea seguro es que los pasos sean deterministas: si un paso se re-ejecuta (porque el checkpoint aún no se había completado cuando ocurrió el fallo), debe producir el mismo resultado. Esta es la responsabilidad del programador en el SDK. En nuestra implementación del contador, garantizamos esto diseñando cada paso como una función pura dado el mismo estado de entrada.

### 2.5 Implicaciones para el diseño de sistemas distribuidos

La llegada de durable functions nativas en AWS Lambda habilita una clase de aplicaciones que antes requerían infraestructura significativa o compromisos de diseño costosos. Identificamos cuatro patrones arquitectónicos que se vuelven prácticos:

#### 2.5.1 Pipelines de agentes de IA con estado

Los flujos de trabajo de agentes de IA (LLM + herramientas + memoria) requieren orquestación de múltiples llamadas a APIs externas con recuperación ante fallos. Cada llamada a un modelo o herramienta es un paso potencialmente costoso que no debe re-ejecutarse si ya tuvo éxito. AWS anuncia explícitamente durable functions para este caso de uso. El modelo checkpoint-and-replay proporciona exactamente la garantía necesaria: si una cadena de pasos falla a mitad, la ejecución retoma desde el último paso checkpointed sin pagar por el trabajo ya realizado.

#### 2.5.2 Procesamiento ETL de larga duración

Pipelines de transformación de datos que procesan grandes volúmenes en múltiples etapas se benefician de la recuperabilidad automática. En el contexto de la Fase 2, la codificación de vídeo es un ejemplo: si el paso de merge falla (como observamos en `vid_merge_fail_always_001`), los chunks ya codificados no necesitan re-procesarse. Sin el paralelismo funcional, sin embargo, el beneficio de latencia es limitado.

#### 2.5.3 Workflows humanos con aprobaciones

La primitiva `context.wait_for_event()` permite suspender una ejecución durable esperando una señal externa — un patrón human-in-the-loop. Esto era antes posible solo con AWS Step Functions, que requiere orquestación explícita separada del código de la función. Con durable functions, el código de orquestación vive junto al código de negocio, reduciendo la fragmentación arquitectónica.

#### 2.5.4 Coordinación de microservicios con garantías de recuperación

En arquitecturas de microservicios donde múltiples servicios deben ejecutarse en secuencia (saga pattern), las durable functions pueden actuar como el coordinador. Cada llamada a un microservicio externo es un paso; si el coordinador falla, reanuda desde el último paso exitoso. Esto es conceptualmente similar al patrón de orquestación de sagas, pero sin requerir una base de datos de estado de saga separada.

## 3. Conexión con la Implementación: Retroalimentación Teoría-Práctica

### 3.1 El contador como actor clásico

La elección del contador como primera evaluación no es arbitraria — es el ejemplo de libro de texto de un actor en el sentido clásico, citado explícitamente por Agha (1985) y por la encuesta de Spenger et al. (2024). Nuestra implementación de Fase 1 permite verificar empíricamente si AWS Lambda Durable Functions satisfacen las propiedades actoriales básicas.

La operación `apply_counter_operation` mapea directamente al procesamiento de un mensaje por un actor: recibe el estado actual (`value, version`), aplica la operación, y produce el nuevo estado. El SDK garantiza que esta operación se ejecuta secuencialmente — nunca en paralelo con otra operación sobre el mismo execution_name. Esto es la **propiedad de no-racing** de los actores, y nuestros resultados de `counter_concurrent_001` la confirman: invocaciones concurrentes producen ejecuciones durables independientes, cada una con su propio estado aislado.

Sin embargo, hay una diferencia crítica respecto al modelo de actores clásico: el contador durable de AWS *no mantiene estado entre invocaciones* del mismo modo que un actor clásico. Cada ejecución durable es un flujo de trabajo nuevo con estado inicial pasado como parámetro. El estado del contador se pasa explícitamente en el evento de entrada (`"state": {"value": 0, "version": 0}`) y se actualiza a través del checkpoint interno. Esto contrasta con Azure Durable Entities, donde el estado de la entidad contador persiste en el almacén entre llamadas a operaciones sobre la misma entidad.

### 3.2 El pipeline de vídeo y el patrón scatter-gather

El pipeline de codificación de vídeo de Fase 2 intenta implementar el patrón *scatter-gather* de actores: un actor coordinador divide el trabajo en sub-tareas (scatter), cada sub-tarea es procesada por un agente independiente, y los resultados se agregan (gather). En el modelo clásico de ExCamera (Fouladi et al., 2017), este patrón se logra con miles de funciones Lambda concurrentes coordinadas mediante un registro de estado en S3.

Nuestra evaluación demuestra que AWS Lambda Durable Functions *intentan* abstraer este patrón mediante `context.parallel()`, pero la implementación no es funcional en el SDK Python v12–v13. Esto no es simplemente una limitación técnica temporal — refleja un desafío fundamental en el modelo: serializar callables Python para distribuirlos a sub-ejecuciones requiere un protocolo de serialización más sofisticado del que el SDK actualmente implementa.

Esta observación tiene implicaciones para la investigación: los sistemas de actores serverless que soportan verdadero paralelismo (como Sprocket o Cloudburst) requieren mecanismos de dirección dinámica de actores hijo y comunicación entre ellos. Las durable functions, al carecer de esto, no pueden replicar el rendimiento de sistemas diseñados explícitamente para el paralelismo serverless.

### 3.3 Suposiciones implícitas de diseño y su alineación con la semántica de actores

Al diseñar ambas implementaciones, adoptamos implícitamente suposiciones que se alinean con la semántica de actores. Primero, diseñamos cada paso como una **función pura dado el mismo estado de entrada**: `apply_counter_operation(state={"value":0}, operation="increment")` siempre devuelve `{"value":1}`. Esta *determinismo de pasos* es requisito del modelo checkpoint-and-replay y equivale a la propiedad de reproducibilidad de los actores en sistemas con event sourcing.

Segundo, usamos el `execution_name` como **clave de idempotencia** — exactamente como la dirección de un actor se usa para garantizar que múltiples mensajes al mismo actor sean procesados por la misma entidad. La diferencia es que en el modelo clásico, la identidad del actor es durable indefinidamente, mientras que en AWS Durable Functions el execution_name caduca tras el período de retención (14 días por defecto).

Tercero, el pipeline de vídeo naturalmente formó un patrón **coordinador-trabajadores**: la ejecución durable actúa como coordinador, y cada invocación de `encode_chunk` actúa como un trabajador sin estado. En un sistema de actores completo, cada chunk tendría su propio actor con identidad, mailbox y estado. En nuestra implementación, los chunks son pasos secuenciales dentro del mismo actor coordinador — una simplificación que funciona secuencialmente pero que no escala paralelamente.

## 4. Síntesis: Posicionamiento en el Paper WOSC 2026

Este análisis proporciona el material para enriquecer la Sección 7 del paper (actualmente titulada "Discusión") y la Sección 2 (Antecedentes) con un posicionamiento teórico sólido. Proponemos los siguientes argumentos estructurantes para el artículo:

Argumento 1 — Nuevas primitivas, viejo paradigma. AWS Lambda Durable Functions no inventan una abstracción nueva: implementan, dentro de las restricciones del modelo de facturación serverless, las propiedades de los sistemas de actores que la comunidad investigadora ha identificado como necesarias para el serverless con estado. La contribución de AWS es integrar estas propiedades nativamente en el runtime Lambda, eliminando la necesidad de frameworks externos (Temporal, Conductor) o capas de investigación (Cloudburst, Crucial).

Argumento 2 — La restricción del paralelismo es sistémica. La no funcionalidad de `context.parallel()` no es solo un bug del SDK Python: refleja el desafío fundamental de implementar actores hijo en un modelo de ejecución donde cada invocación Lambda es independiente y efímera. Para que el paralelismo funcione, el runtime necesita un mecanismo de dirección dinámica entre ejecuciones y un protocolo de coordinación padre-hijo. Este es el problema que sistemas como Sprocket y ExCamera resuelven con diseños arquitectónicos específicos — y que el SDK durable de AWS aún no resuelve.

Argumento 3 — El coste de la durabilidad. El sobrecoste de 1.28–1.79× que observamos respecto al enfoque tradicional refleja el precio de las garantías actoriales: serialización de estado, persistencia de checkpoint, y múltiples invocaciones Lambda internas. Azure Durable Entities incurre en costes similares. Orleans, al mantener el estado en memoria, evita este coste — pero requiere silos dedicados con costo de infraestructura fijo. Para la comunidad de investigación serverless, este trade-off es una contribución de medición original.

Argumento 4 — Posición en la taxonomía de Spenger et al. Usando el marco de Spenger et al. (2024), AWS Lambda Durable Functions se clasifican como un sistema de *reliable actor orchestration* con cobertura parcial de las dimensiones: gestión de estado (✅ automática), paso de mensajes (❌ ausente), composición (⚠️ secuencial, no paralela), tolerancia a fallos (✅ retry+replay), y ordenamiento (✅ secuencial estricto). Esta clasificación formal da rigor académico al posicionamiento del paper.

## Referencias

[S24] Spenger, J., Carbone, P., y Haller, P. (2024). A Survey of Actor-Like Programming Models for Serverless Computing. En *Active Object Languages: Current Research Trends*, Lecture Notes in Computer Science, vol. 14360, pp. 123–146. Springer, Cham. https://doi.org/10.1007/978-3-031-51060-1_5

[G73] Hewitt, C., Bishop, P., y Steiger, R. (1973). A Universal Modular ACTOR Formalism for Artificial Intelligence. En *Proc. 3rd International Joint Conference on Artificial Intelligence (IJCAI '73)*, pp. 235–245.

[A85] Agha, G. A. (1986). *ACTORS: A Model of Concurrent Computation in Distributed Systems*. MIT Press. ISBN 9780262010948.

[Gi23] Gillum, C., Burckhardt, S., Chronister, C., Fox, C., Langworthy, D., y Zhao, L. (2023). Durable Functions: Semantics for Stateful Serverless. *Proc. ACM Program. Lang.* 7, OOPSLA2, Article 248. https://doi.org/10.1145/3622845

[B14] Bernstein, P. A., y Bykov, S. (2014). Developing Cloud Services Using the Orleans Virtual Actor Model. *IEEE Internet Computing*, 18(5), 49–56. https://doi.org/10.1109/MIC.2014.87

[MS26] Microsoft Learn (2026). Durable entities — Azure Functions. https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-entities

[Sr20] Sreekanti, V., Wu, C., Lin, X. C., Schleier-Smith, J., Gonzalez, J. E., Hellerstein, J. M., y Tumanov, A. (2020). Cloudburst: Stateful Functions-as-a-Service. *Proc. VLDB Endow.*, 13(11), 2438–2452.

[Po22] Pons, D. B., Sutra, P., Artigas, M. S., París, G., y López, P. G. (2022). Stateful Serverless Computing with Crucial. *ACM Trans. Softw. Eng. Methodol.*, 31(3), 39:1–39:38. https://doi.org/10.1145/3490386

[Sp22] Spenger, J., Carbone, P., y Haller, P. (2022). Portals: An Extension of Dataflow Streaming for Stateful Serverless. En *Proceedings of Onward! 2022*, ACM. https://doi.org/10.1145/3563835.3567664

[Fo17] Fouladi, S., Wahby, R. S., Shacklett, B., Balasubramaniam, K., Zeng, W., Bhalerao, R., Sivaraman, A., Barrett, G., y Winstein, K. (2017). Encoding, Fast and Slow: Low-Latency Video Processing Using Thousands of Tiny Threads. En *NSDI '17*. USENIX Association.

[Zh21] Zhu, H., Cardoza, A., Chen, P. B., Angel, S., y Liu, V. (2021). Fault-Tolerant and Transactional Stateful Serverless Workflows. En *OSDI '21*. USENIX Association.

[AWS25] Amazon Web Services (2025). Build multi-step applications and AI workflows with AWS Lambda Durable Functions. AWS Blog, diciembre 2025. https://aws.amazon.com/blogs/aws/build-multi-step-applications-and-ai-workflows-with-aws-lambda-durable-functions/
