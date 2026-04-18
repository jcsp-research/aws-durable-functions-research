# Test Case: video_invalid_format_001 (Validación de Dominio - Durable)

**Status:** ✅ Succeeded (HTTP 400 - Validación rápida)  
**Execution Date:** 2026-04-18 13:17:50 UTC  
**Duration:** 1.985 segundos  
**Execution Model:** durable  

## Configuración
- **Formato inválido:** `avi` (no soportado)
- **Comportamiento esperado:** Fallo rápido de dominio sin reintentos

## Secuencia de Ejecución

| Paso | Estado | Duración | Observación |
|------|--------|----------|-------------|
| initialize_job | ✅ Succeeded | 168 ms | Job inicializado |
| validate_video | ✅ Succeeded (domain_error) | 0 ms | Detectó formato inválido |
| **Resultado** | **HTTP 400** | - | Early exit, no reintentos |

## JSON Output

```json
{
  "statusCode": 400,
  "body": {
    "message": "fase2-video-durable validation failed",
    "job_id": "46eb7ea4-82f7-4bb3-8cee-ff213e7d406f",
    "video_id": "video-004",
    "status": "validation_failed",
    "error_type": "domain_validation",
    "error_message": "Unsupported input format: avi",
    "execution_model": "durable"
  }
}


Insight: Domain Error vs Runtime Error
El runtime no reintentó la validación fallida (distinguish entre domain validation y execution error). Esto demuestra que:
Errores de dominio (400): Fallo inmediato, sin retry
Errores de ejecución (500): Reintentos automáticos según política



