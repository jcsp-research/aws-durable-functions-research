# Informe Fase 2: Evaluación Empírica de Estrategias Serverless para Pipeline de Video

**Autor:** Julio Siguenaspacheco  
**Programa:** Doctorado, Universitat Rovira i Virgili  
**Fecha:** Abril 2026  
**Versión:** 1.0 (entregable doctoral)

## 1. Resumen Ejecutivo

Este estudio compara empíricamente dos estrategias de orquestación serverless para pipelines de procesamiento de video bajo restricciones FaaS:

1. **Enfoque Durable:** AWS Step Functions con checkpointing automático y paralelismo declarativo (SDK experimental)
2. **Enfoque Traditional:** Orquestación manual mediante Lambda + DynamoDB + retries explícitos

**Hallazgo principal (condicionado):** En ausencia de fallos reales, el enfoque traditional es **40% más rápido** (4.0s vs 6.8s) y **32% más barato**, con un overhead de I/O explícito medible (17 reads, 10 writes). La ventaja del durable en recuperación ante fallos **no pudo validarse** debido a estado residual en tabla de markers.

## 2. Metodología

### 2.1 Implementaciones Isomórficas
Ambas implementaciones ejecutan idéntica lógica de negocio (validate → split → encode → merge) diferenciándose únicamente en estrategia de estado:

| Aspecto | Durable | Traditional |
|---------|---------|-------------|
| **Runtime state** | Step Functions (automático) | DynamoDB (manual) |
| **Error handling** | Automático (replay) | Manual (MAX_RETRIES=2) |
| **Paralelismo** | Map state nativo (falló en test) | Secuencial nativo |
| **Observability** | Execution event history | CloudWatch + contadores I/O explícitos |

### 2.2 Carga de Trabajo
- **Video sintético:** 60s, 1080p, 6 chunks de 10s cada uno
- **Simulación CPU:** `time.sleep(100 + 50×duration_ms)` por chunk
- **Fallo inyectado:** `fail_mode: "once"` en `encode_chunk` (no activado por marker pre-existente)

### 2.3 Métricas Capturadas
Todas las métricas se emiten vía logs estructurados (`METRIC {json}`):
- `execution_duration`: Latencia E2E
- `checkpoint_size` / `explicit_state_size`: Estado persistido (KB)
- `dynamodb_reads/writes`: I/O explícito (solo traditional)
- `parallelism_summary`: Grado de paralelismo efectivo

## 3. Resultados

### 3.1 Latencia End-to-End (Tabla 1)

| Modelo | E2E Latency (ms) | Billed Duration (ms) | Overhead vs Mínimo |
|--------|------------------|----------------------|-------------------|
| **Durable** | 6,751.339 | ~6,750 | +67% (runtime SDK) |
| **Traditional** | 4,032.595 | 4,598 | Base (0%) |

**Análisis:** El durable presenta un overhead constante de ~2.7s atribuible a:
- Intentos fallidos de paralelismo (`BatchResult` no materializable)
- Fallback a secuencial después de 2 intentos
- Serialización de estado entre steps del runtime

### 3.2 Costo Computacional (Tabla 2)
| Modelo | Compute Cost ($) | I/O Cost ($) | Total ($) |
|--------|------------------|--------------|-----------|
| **Durable** | ~0.00034 | ~0 | ~0.00034 |
| **Traditional** | ~0.00023 | ~0.000013 | ~0.00024 |

**Nota:** Precios us-east-2 (Lambda: $0.0000166667/GB-s, DynamoDB: on-demand)

### 3.3 Complejidad de Estado (Tabla 3)
| Modelo | Tamaño (KB) | Versiones | I/O Ops |
|--------|-------------|-----------|---------|
| **Durable** | 3.305 | 3 | ~5 (estimado interno) |
| **Traditional** | 3.988 | 9 | 27 (17 reads + 10 writes) |

### 3.4 Recuperación ante Fallos (No Validado)
El test de fallo transitorio (`fail_mode: "once"`) **no activó el mecanismo de retry** porque el marker `phase2-encode-once-001` ya existía en la tabla `durable-failure-markers` de ejecución previa.

**Impacto:** No se pudo medir:
- MTTR (Mean Time To Recovery)
- Diferencia entre retry automático (durable) vs manual (traditional)
- Sobrecarga de I/O adicional por reintentos

## 4. Discusión

### 4.1 Trade-offs Académicos Documentados
- **Consistencia vs. Latencia:** El modelo durable prioriza ACID state sacrificando latencia media (factor 1.67x)
- **Complejidad de código:** El traditional requirió ~340 LOC de manejo de errores vs ~45 en durable (factor 7.5x)
- **Transparencia vs. Abstracción:** Traditional expone métricas de I/O detalladas (17 reads, 10 writes); durable oculta overhead en runtime

### 4.2 Limitaciones del Estudio
1. **SDK inmaduro:** Fallo en materialización de `BatchResult` impidió evaluar paralelismo real
2. **Contaminación de estado:** Marker de fallo pre-existente invalidó test de recuperación
3. **Simulación computacional:** No se utilizó ffmpeg real (limitación FaaS sin GPU)

## 5. Conclusiones y Trabajo Futuro

1. **Recomendación condicionada:** Para pipelines de video &lt;2min sin requisitos estrictos de resiliencia, el traditional es más eficiente. Para videos largos con tolerancia a fallos, el durable podría ser superior (pendiente validación con marker limpio).

2. **Optimización futura:** 
   - Implementar differential checkpointing para reducir overhead de I/O en durable
   - Corregir materialización de `BatchResult` en SDK para habilitar paralelismo real

3. **Fase 3:** 
   - Re-ejecutar `fail_once` con tabla de markers limpia para validar recuperación
   - Integrar GPU (Lambda GPU support) para evaluar overhead bajo carga real

## Referencias
- AWS Lambda Documentation (2026)
- Step Functions Developer Guide, "Error Handling and Retries"
- Logs experimentales: `./experiments/` (repositorio Git adjunto)

---
**Anexos:** Código fuente en `phase2/src/`, datos crudos en logs de CloudWatch `/aws/lambda/phase2-video-durable` y `/aws/lambda/fase2-video-traditional`.