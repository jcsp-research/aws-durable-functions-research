# Análisis: Fail Once Encoding (vid_enc_fail_once_001)
**Test:** Fallo transitorio en etapa de encoding | **Fecha:** 2026-04-18

## Configuración
- **Video:** 60s, 1080p, 6 chunks de 10s
- **Fallo inyectado:** `encode_chunk` con `fail_mode: "once"`
- **Objetivo:** Comparar mecanismos de recuperación automática vs manual

## Resultados Durable Functions
- **Latencia:** 6,751.339 ms (~6.8s)
- **Checkpoint:** 3.305 KB (state_version: 3)
- **Execution Model:** `durable_sequential_fallback`
- **Recovery:** Automático (runtime SDK)
- **Status:** 200 (success)

## Resultados Traditional
- **Latencia:** 4,032.595 ms (~4.0s)
- **Estado:** 3.988 KB (state_version: 9)
- **DynamoDB:** 17 reads, 10 writes
- **Failure Markers:** 0 ⚠️
- **Recovery:** Manual (`execute_with_retries` con MAX_RETRIES=2)
- **Status:** 200 (success)

## Análisis Crítico
### Anomalía Detectada
El contador `failure_marker_writes: 0` indica que el marker `phase2-encode-once-001` **ya existía** en la tabla DynamoDB de una ejecución previa.

**Impacto:**
- ❌ No se activó el fallo transitorio real
- ❌ No se pudo medir diferencia de MTTR (Mean Time To Recovery)
- ✅ Ambos procesaron como happy path efectivo

### Métricas Comparativas
| Métrica | Durable | Traditional | Delta |
|---------|---------|-------------|-------|
| Latencia | 6,751 ms | 4,033 ms | -40% |
| I/O Ops | ~5 (est.) | 27 (medido) | -81% |
| Complejidad | 45 LOC | 340 LOC | -87% |

## Conclusión
Aunque el Traditional es 40% más rápido y expone I/O medible, **no se validó la hipótesis de recuperación ante fallos** debido a contaminación de estado previa. Se requiere re-ejecución con tabla de markers limpia.

## Recomendación
Para validar verdaderamente el mecanismo de retry:
1. Limpiar tabla `durable-failure-markers` en DynamoDB
2. Usar nuevo `failure_key` (ej: `phase2-encode-once-002`)
3. Re-ejecutar y capturar logs de reintento en ambas arquitecturas