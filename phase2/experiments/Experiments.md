# Fase 2: Especificación de Experimentos

**Fecha:** 2026-04-06  
**Plataforma:** AWS Lambda Durable Functions (Preview)  
**Región:** us-east-2  

---

## Resumen de Tests

| ID | Nombre | Tipo | Estado | Duración | Objetivo |
|----|--------|------|--------|----------|----------|
| EXP-001 | video_happy_path_001 | Baseline | ✅ Succeeded | 10.0s | Validar flujo completo |
| EXP-002 | vid_enc_fail_once_001 | Retry | ✅ Succeeded | 48.2s | Validar recuperación transitoria |
| EXP-003 | vid_merge_fail_always_001 | Circuit Breaker | ❌ Failed* | 3m 30s | Validar límite de reintentos |
| EXP-004 | video_invalid_format_001 | Domain Error | ⚠️ 400 Bad Request | 2.8s | Validar fail-fast |

*\* Fallo esperado y correcto*

---

## EXP-001: Happy Path (Baseline)

### Objetivo
Validar el flujo completo del pipeline sin inyección de fallos, estableciendo métricas baseline de latencia y costo.

### Configuración

```json
{
  "test_case": "video_happy_path_001",
  "video": {
    "video_id": "video-001",
    "input_uri": "s3://durable-video-artifacts/input/sample.mp4",
    "format": "mp4",
    "duration_seconds": 95,
    "resolution": "1080p"
  },
  "encoding": {
    "codec": "h264",
    "bitrate_kbps": 2200,
    "chunk_duration_seconds": 10
  },
  "failures": {
    "validate_video": { "fail_mode": "none" },
    "split_video": { "fail_mode": "none" },
    "encode_chunk": { "fail_mode": "none" },
    "merge_video": { "fail_mode": "none" }
  }
}