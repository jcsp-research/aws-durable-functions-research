# Fase 1: Observaciones Experimentales - Contador Durable
## Orquestación Serverless de GPU para Pipelines RAG bajo Restricciones FaaS

**Autor:** Julio Siguenaspacheco  
**Institución:** Universitat Rovira i Virgili (URV)  
**Fecha de experimentación:** 2026-04-06  
**Versión:** 1.0.0  
**Estado:** Fase 1 Completada y Validada

---

## 1. Resumen Ejecutivo

Se completó la validación empírica de la Fase 1 del proyecto doctoral, centrada en la demostración de **entidades durables** (Durable Entities) mediante un contador stateful implementado en AWS Lambda. 

Los experimentos confirman que el modelo de *checkpoint-and-replay* garantiza persistencia de estado, tolerancia a fallos transitorios y aislamiento de ejecuciones concurrentes, estableciendo la base técnica para la orquestación de workflows RAG en Fase 2.

**Hallazgo principal:** El sistema mantiene consistencia estricta del estado (value/version) a través de fallos, recuperaciones y ejecuciones paralelas, con un overhead de recuperación del ~25% y granularidad de 3 steps por operación.

---

## 2. Diseño Experimental

### 2.1 Arquitectura del Sistema
- **Plataforma:** AWS Lambda Durable Functions (us-east-2)
- **Runtime:** Python 3.12
- **Patrón:** Durable Entity (counter stateful)
- **Mecanismo de persistencia:** Checkpoint automático por step (initialize → apply → build)

### 2.2 Batería de Pruebas
Se ejecutaron **14 ejecuciones** (12 escenarios únicos) estructurados en 4 categorías:

| Categoría | Tests | Objetivo de Validación |
|-----------|-------|------------------------|
| **Operaciones CRUD** | normal_inc_001, normal_dec_001, normal_get_001 | Funcionalidad básica y persistencia |
| **Tolerancia a Fallos** | fail_once_inc_001, fail_always_inc_001 | Checkpoint-and-replay y límites de reintentos |
| **Concurrencia** | concurrent_inc_1, concurrent_inc_2, concurrent_inc_3 | Aislamiento de entidades y race conditions |
| **Idempotencia** | idempotency_same_execution_001 (×2) | Consistencia ante re-ejecución |

---

## 3. Resultados Cuantitativos

### 3.1 Métricas de Rendimiento Base

| Métrica | Valor Medio | Rango | Unidad |
|---------|-------------|-------|--------|
| **Latencia end-to-end** | 850 | 754 – 932 | ms |
| **Duración step crítico** (apply_operation) | 202 | 18 – 284 | ms |
| **Duración inicialización** (initialize) | ~20 | &lt; 50 | ms |
| **Tamaño de checkpoint** | 0.025 | Constante | KB |
| **Memoria utilizada** | ~45 | 40 – 50 | MB |
| **Tiempo cold-start** | ~800 | 650 – 950 | ms |

### 3.2 Análisis de Tolerancia a Fallos

| Escenario | Duración Total | Reintentos | Resultado | Overhead |
|-----------|----------------|------------|-----------|----------|
| **Ejecución limpia** (baseline) | 1.8 s | 0 | Success | 0% |
| **Fallo transitorio** (fail_once) | 2.26 s | 1 implícito | Success | +25% |
| **Fallo permanente** (fail_always) | ~3.5 min | 5 | Failed* | N/A |

*Fallo controlado esperado tras agotar política de reintentos.

**Observación crítica:** El step `apply_counter_operation` muestra aumento de latencia de ~18 ms (normal) a ~223 ms (con retry), evidenciando el mecanismo de replay que re-ejecuta el step fallido sin re-procesar steps previos completados.

### 3.3 Consistencia de Estado

| Test | Estado Inicial | Estado Final | Versión | Delta |
|------|----------------|--------------|---------|-------|
| normal_inc_001 | (0, 0) | (1, 1) | +1 | +1 |
| normal_dec_001 | (10, 3) | (9, 4) | +1 | -1 |
| normal_get_001 | (7, 2) | (7, 2) | 0 | 0 (lectura) |
| idempotency_001 (1ra) | (0, 0) | (3, 1) | +1 | +3 |
| idempotency_001 (2da) | (0, 0) | (3, 1) | +1 | +3 |

**Conclusión de consistencia:** Las operaciones concurrentes sobre el mismo estado inicial generaron entidades independientes (Execution Names únicos), garantizando aislamiento sin race conditions. Las re-ejecuciones idempotentes produjeron resultados matemáticamente idénticos.


### 3.4 Estimación de Costes y Comparativa Económica

Basado en la tarifa de AWS Lambda (us-east-2, 2026): $0.20 por millón de solicitudes + $0.0000166667 por GB-segundo.

#### Costo por Operación - Durable Functions

| Escenario | Duración | Memoria | GB-segundos | Costo Compute | Costo Request | **Total** |
|-----------|----------|---------|-------------|---------------|---------------|-----------|
| **Ejecución limpia** (baseline) | 1.8 s | 128 MB | 0.225 | $0.00000375 | $0.00000020 | **$0.00000395** |
| **Con retry** (fail_once) | 2.26 s | 128 MB | 0.2825 | $0.00000471 | $0.00000020 | **$0.00000491** |
| **Fallo permanente** (fail_always) | 210 s | 128 MB | 26.25 | $0.0004375 | $0.00000020 | **$0.0004377** |

*Nota: El costo de almacenamiento de checkpoints (0.025 KB) es despreciable ($0.023 por GB-mes), equivalente a ~$0.0000000006 por operación.*

#### Comparativa: Lambda Durable vs Lambda + DynamoDB (Enfoque Tradicional)

**Escenario:** Contador con 1,000 operaciones/día (30% incrementos, 20% decrementos, 50% lecturas)

| Métrica | Lambda Durable | Lambda + DynamoDB | Diferencia |
|---------|----------------|-------------------|------------|
| **Costo por operación** | ~$0.000004 | ~$0.0000015 | Durable es 2.6× más caro |
| **Latencia p95** | ~850 ms | ~150 ms* | Tradicional es 5.6× más rápido |
| **Complejidad código** | Baja (estado implícito) | Media (gestión explícita BD) | Durable reduce LOC ~40% |
| **Tolerancia a fallos** | Nativa (retry automático) | Implementación manual | Durable ahorra desarrollo |
| **Cold-start** | ~800 ms | ~100 ms | Durable tiene overhead |

*DynamoDB latencia típica: 10-50ms + Lambda 50-100ms sin checkpoint overhead.

**Cálculo detallado enfoque tradicional:**
- Lambda (50ms ejecución): $0.0000003 (compute + request)
- DynamoDB on-demand:
  - Writes (increment/decrement): $0.00000125 por operación
  - Reads (get): $0.00000025 por operación
- **Total promedio ponderado:** (0.5×$0.00000155) + (0.5×$0.00000055) = **$0.00000105 por operación**

#### Análisis de Trade-offs

Aunque Lambda Durable tiene un costo por operación ~2.6× superior al enfoque tradicional, ofrece ventajas operativas significativas:

 1. **Desarrollo:** Reduce tiempo de implementación (no requiere lógica de reintentos ni gestión de transacciones DynamoDB)
 2. **Fiabilidad:** El retry automático evita pérdida de datos ante fallos transitorios (valor incalculable en pipelines críticos)
 3. **Observabilidad:** El historial de ejecución integrado reduce costos de logging/monitoring externos

 **Punto de equilibrio:** Para pipelines RAG (Fase 2), donde el costo de GPU domina ($0.0001-0.001 por inferencia), el overhead del 0.000004 de durabilidad es insignificante (&lt;1%), justificando el uso de Durable Functions por su tolerancia a fallos.

---

## 4. Análisis de Hallazgos

### 4.1 Checkpoint Granularity
El sistema demuestra granularidad fina con **3 steps atómicos** por operación:
1. `initialize_counter`: Setup y validación de estado
2. `apply_counter_operation`: Lógica de negocio (increment/decrement/get)
3. `build_response`: Serialización del resultado

Esta granularidad permite recuperación parcial ante fallos: si `apply` falla, no se re-ejecuta `initialize`, optimizando el overhead de recuperación.

### 4.2 Política de Reintentos (Backoff Exponencial)
El test `fail_always_inc_001` reveló una política de **5 reintentos máximos** con backoff exponencial:
- Intentos 1-2: Inmediatos (~segundos)
- Intentos 3-5: Con delay creciente (~30-40s entre intentos)
- Total hasta fallo permanente: ~3.5 minutos

Esto valida que el sistema no consume recursos indefinidamente ante fallos permanentes (ej. bugs de código), crítico para control de costos en FaaS.

### 4.3 Overhead de Durabilidad
El costo de garantizar durabilidad se mide en:
- **Tiempo:** +25% en fallos transitorios vs baseline
- **Almacenamiento:** 0.025 KB por checkpoint (despreciable para estados simples)
- **Compute:** Steps previos a fallo no se re-ejecutan (optimización de replay)

Para la Fase 2 (pipelines RAG), este overhead es aceptable dado el beneficio de tolerancia a fallos en pipelines de múltiples etapas (embedding → retrieval → generation).


### 4.4 Límites de Timeout y Recuperación ante Delay Prolongado

Se ejecutaron dos variantes del test `manual_termination_recovery_001` 
para mapear el comportamiento ante operaciones de larga duración:

| Configuración | Sleep | Resultado | Mecanismo Observado |
|--------------|-------|-----------|---------------------|
| **Variante A** | 60s | ❌ Failed tras ~11.5min | Lambda service retries (6 intentos) |
| **Variante B** | 15s | ✅ Succeeded en 16.96s | Checkpoint-and-replay normal |

**Hallazgo:** AWS Lambda tiene un límite implícito de ~60s para operaciones 
síncronas antes de activar reintentos del servicio. Para pipelines RAG 
(Fase 2), se recomienda:
- Timeout de Lambda configurado a 5-15 minutos
- O fragmentar operaciones GPU en steps <60s cada uno
- O usar invocación asíncrona para evitar timeout del cliente


### 4.5 Validación de Operaciones y Manejo de Errores de Dominio

El test `invalid_operation_001` reveló un comportamiento crítico del 
mecanismo de reintentos:

**Input:** Operación `multiply` (no implementada en el contador)
**Estado inicial:** `value: 5, version: 2`
**Resultado esperado:** Fallo inmediato por operación no soportada
**Resultado observado:** 5 reintentos automáticos durante 3m 40s antes 
de declarar `ExecutionFailed`

| Métrica | Valor |
|---------|-------|
| Tipo de error | `CallableRuntimeError` |
| Mensaje | "Unsupported operation: multiply" |
| Reintentos | 5 (política máxima) |
| Duración hasta fallo | 3 min 40 s |
| Estado modificado | ❌ No (preservó value: 5) |

**Implicación para Fase 2:** El retry automático de AWS Durable Functions 
no distingue entre:
- Fallos transitorios (red, memoria)
- Errores de lógica de negocio (operación inválida, prompt malformado)

Esto requiere implementar *circuit breakers* o validación temprana en el 
código de la función para evitar reintentos costosos de operaciones 
doomed-to-fail (ej. embeddings con modelo inexistente).


### 4.6 Validación de Configuración (Precondiciones)

El test `missing_failure_key_001` verifica que el sistema implementa 
*fail-fast validation* para configuraciones inconsistentes:

**Escenario:** `fail_mode: "once"` sin proporcionar `failure_key`
**Resultado:** Error inmediato antes de iniciar ejecución durable
**Mensaje:** `"fail_mode='once' requires 'failure_key' in the event"`

**Implicación:** El diseño sigue el principio de "hacer fallar lo antes posible" 
(fail-fast), evitando iniciar workflows durables con configuración incompleta 
que podría resultar en comportamiento indefinido durante reintentos.

Esta validación es crítica para Fase 2 donde los parámetros de configuración 
(por ejemplo, `model_id`, `temperature`, `max_tokens`) deberán ser validados 
antes de iniciar pipelines de inferencia costosos en GPU.

---

## 5. Validación de Requisitos Doctorales

| Requisito Fase 1 | Criterio de Aceptación | Estado | Evidencia |
|------------------|------------------------|--------|-----------|
| **1.1** Operaciones básicas | CRUD funcional con persistencia | ✅ Cumple | 3/3 tests exitosos |
| **1.2** Manejo de errores | Retry automático y límites definidos | ✅ Cumple | fail_once y fail_always validados |
| **1.3** Concurrencia | Aislamiento de entidades | ✅ Cumple | 3 ejecuciones paralelas sin interferencia |
| **1.3** Idempotencia | Resultados determinísticos | ✅ Cumple | Doble ejecución con identical output |
| **1.4** Métricas | Logs estructurados y cuantificables | ✅ Cumple | 14/14 ejecuciones generaron métricas JSON |

---

## 6. Limitaciones Observadas

El principal trade-off identificado es el costo computacional: las Durable Functions 
tienen un overhead de ~$0.000003 por operación vs el enfoque tradicional, 
justificado por la tolerancia a fallos nativa (ver sección 3.4 para cálculos detallados).

1. **Idempotencia de sistema vs aplicación:** AWS genera Execution Names únicos por invocación de consola, por lo que la idempotencia demostrada es a nivel de lógica de aplicación (mismo resultado matemático), no a nivel de sistema (cached replay). Para true deduplicación se requeriría uso de API con `execution_name` explícito.

2. **Latencia de inicialización:** Los 800ms de cold-start incluyen overhead de inicialización del runtime Durable Functions, no presente en Lambdas stateless tradicionales.

3. **Tamaño de estado:** Limitado a 256 KB (límite AWS), aunque nuestros checkpoints de 0.025 KB están muy por debajo del umbral.

**Nota adicional:** Se diseñaron casos de validación para operaciones inválidas (`invalid_operation_001`) y manejo de configuración errónea (`missing_failure_key_001`) como parte de la estrategia de robustez, priorizando la ejecución de escenarios de fallo transitorio y permanente como casos principales de tolerancia a fallos.

---

## 7. Conclusiones y Transición a Fase 2

La Fase 1 establece que **AWS Durable Functions proveen las primitivas necesarias** para orquestar workflows académicos complejos con garantías de estado. Los mecanismos de checkpoint-and-replay funcionan según especificación, permitiendo recuperación ante fallos de red o timeouts sin pérdida de progreso.

**Próximos pasos (Fase 2):**
1. Extender el patrón a workflows multistep (chains): Preprocessing → Embedding → Vector Search → LLM Inference
2. Implementar manejo de estado compartido entre funciones (orquestador vs workers)
3. Medir overhead en pipelines GPU (cold-start de contenedores CUDA + inicialización de modelo)
4. Diseñar políticas de timeout específicas para operaciones de inferencia (&gt;10s)

---

## 8. Anexos

### A. Logs Representativos
**Métrica estructurada (JSON):**
```json
{
  "metric_type": "checkpoint_size",
  "test_case": "idempotency_same_execution_001",
  "size_kb": 0.025,
  "state_version": 1,
  "counter_value": 3
}