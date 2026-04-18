# Observaciones de Ejecución - Fase 2 (Consolidado)
**Autor:** Julio Siguenaspacheco | **Fecha:** 2026-04-18 | **Doctorado URV**

## Resumen Ejecutivo
Se ejecutaron 4 escenarios comparando arquitecturas Durable vs Traditional para pipeline de video RAG.

---

## Experimento 1: Happy Path (video_happy_path_001)
**Configuración:** Video 95s, 1080p, 10 chunks, sin fallos.

### Resultados
- **Durable:** 9,496 ms, 5.164 KB estado, v3, fallback secuencial
- **Traditional:** 6,241 ms, 6.302 KB estado, v13, 39 I/O ops
- **Overhead Durable:** +3.3s (52% más lento) por intentos de paralelismo fallidos

---

## Experimento 2: Fail Once (vid_enc_fail_once_001)  
**Configuración:** Video 60s, 6 chunks, fallo transitorio en encode.

### Resultados
- **Durable:** 6,751 ms, recovery automático (runtime), status 200
- **Traditional:** 4,033 ms, recovery manual (MAX_RETRIES=2), 27 I/O ops
- **⚠️ Anomalía:** `failure_marker_writes: 0` indica marker pre-existente. No se activó fallo real.

---

## Experimento 3: Fail Always (vid_merge_fail_always_001) 🔴
**Configuración:** Video 45s, 3 chunks, fallo permanente en merge.

### Resultados Críticos
- **Durable:** 58,000 ms (~58s) antes de fallar, status 500
- **Traditional:** 2,701 ms con circuit-breaker (3 intentos), status 500
- **Hallazgo:** Traditional es **21x más rápido** en manejo de fallos permanentes
- **Log Traditional:** 

Retrying step=merge_video attempt=1/2
Retrying step=merge_video attempt=2/2
Circuit breaker opened after 3 attempts



---

## Experimento 4: Invalid Format (video_invalid_format_001)
**Configuración:** Video 30s, formato `avi` no soportado.

### Resultados
- **Traditional:** 70 ms, 3 I/O ops (1r/2w), status 400
- **Durable:** 831 ms, ~2 I/O ops, status 400
- **Validación:** Ambos rechazan correctamente, pero Durable tiene 12x más overhead

---

## Comparativa Consolidada

| Métrica | Happy | Fail Once | Fail Always | Invalid |
|---------|-------|-----------|-------------|---------|
| Durable Lat | 9,497 | 6,751 | 58,000 | 831 |
| Trad Lat | 6,241 | 4,033 | 2,701 | 70 |
| Speedup Trad | 1.5× | 1.7× | **21.5×** | **11.9×** |
| Trad I/O | 39 | 27 | 18 | 3 |

## Hipótesis Validadas
1. ❌ Durable NO reduce latencia en happy path (overhead 34-52%)
2. ✅ Traditional expone I/O completamente (medible vs opaco)
3. ❌ Durable NO es más rápido en recuperación (21× más lento en fallos permanentes)
4. ✅ Traditional tiene circuit-breaker efectivo vs retries opacos del SDK

## Próximos Pasos
- Limpiar tabla `durable-failure-markers` para re-ejecutar fail_once
- Investigar configuración `nonRetryableErrors` en SDK Durable

