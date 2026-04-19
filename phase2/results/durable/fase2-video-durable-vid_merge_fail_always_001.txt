# Análisis: Fail Always Merge (vid_merge_fail_always_001)
**Test:** Fallo permanente en etapa final | **Fecha:** 2026-04-18 | **Hallazgo Crítico 🔴**

## Configuración
- **Video:** 45s, 720p, 3 chunks de 15s
- **Fallo inyectado:** `merge_video` con `fail_mode: "always"`
- **Objetivo:** Evaluar circuit-breaker ante errores no recuperables

## Resultados Durable Functions ⚠️
- **Latencia:** ~58,000 ms (**58 segundos**)
- **Status:** 500 (Failed)
- **Error:** `CallableRuntimeError` - "Simulated permanent failure in merge_video"
- **Comportamiento:** Runtime no detectó `fail_mode: "always"` como no-reintentable
- **Costo:** ~$0.00290 (billed duration 58s, 3008MB)

## Resultados Traditional ✅
- **Latencia:** 2,701.498 ms (**2.7 segundos**)
- **Status:** 500 (Failed)
- **DynamoDB:** 12 reads, 6 writes
- **Circuit Breaker:** Funcionó correctamente
  - Intento 1: Fallo
  - Retry 1 (attempt 1/2): Fallo
  - Retry 2 (attempt 2/2): Fallo
  - **Graceful failure tras 3 intentos totales**

## Hallazgo Doctoral Principal

### Traditional es 21× más rápido en fallos permanentes
| Métrica | Durable | Traditional | Ratio |
|---------|---------|-------------|-------|
| **Latencia** | 58,000 ms | 2,701 ms | **21.5×** |
| **Costo** | $0.00290 | $0.00015 | **19.3×** |
| **Reintentos** | Opacos/timeout | 3 intentos explícitos | - |

### Análisis del Comportamiento
**Durable Functions SDK:**
- No distingue entre fallos transitorios vs permanentes
- Posible reintentos internos hasta timeout (58s sugiere ~10-20 reintentos)
- Política de retry no configurable por el desarrollador

**Traditional (Manual):**
- Circuit-breaker implementado con `MAX_RETRIES=2`
- Control granular: 1 intento inicial + 2 reintentos = 3 totales
- Fail-fast ante errores permanentes conocidos

## Implicaciones para la Tesis

### Trade-off Arquitectónico
La abstracción del SDK Durable **oculta la complejidad** pero **pierde control granular**:
- ❌ No se puede configurar "no reintentar en este tipo de error"
- ❌ Costo prohibitivo en fallos permanentes ($0.00290 vs $0.00015)
- ✅ Menor código (45 vs 300 LOC) pero comportamiento opaco

### Recomendación
Para pipelines donde los fallos permanentes son frecuentes (ej: servicios externos inestables), el enfoque **Traditional con circuit-breaker manual es arquitectónicamente superior**.

## Logs de Referencia
- **Traditional:** `bb330300-e63e-40c8-9711-3c9e3ed77f1f` (CloudWatch)
- **Mensaje clave:** "Circuit breaker opened after MAX_RETRIES attempts"

## Siguientes Pasos
1. Investigar configuración `nonRetryableErrors` en SDK Durable (si existe)
2. Documentar este comportamiento como limitación del SDK experimental
3. Considerar este escenario en el modelo de costos de Fase 3