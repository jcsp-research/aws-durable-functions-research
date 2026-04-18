
---

### 2. `phase2/results/video_invalid_format_001_traditional.md`

```markdown
# Test Case: video_invalid_format_001 (Validación de Dominio - Traditional)

**Status:** ✅ Succeeded (HTTP 400 - Validación rápida)  
**Execution Date:** 2026-04-18 13:20:40 UTC  
**Duration:** 64.58 ms (billed: 67 ms)  
**Execution Model:** traditional_sequential_with_explicit_state  

## Métricas Clave

| Métrica | Valor |
|---------|-------|
| DynamoDB Reads | 1 |
| DynamoDB Writes | 2 |
| Tiempo Total | 64.58 ms |
| Overhead I/O | Mínimo (solo init + validación) |

## JSON Output

```json
{
  "statusCode": 400,
  "body": {
    "message": "fase2-video-traditional validation failed",
    "job_id": "c624c6cc-1076-4c24-87c4-da9cf0c11680",
    "video_id": "video-004",
    "status": "validation_failed",
    "error_type": "domain_validation",
    "error_message": "Unsupported input format: avi",
    "execution_model": "traditional_sequential_with_explicit_state"
  }
}  


Comparativa: Durable vs Traditional (Validación) 


| Aspecto      | Durable                | Traditional           |
| ------------ | ---------------------- | --------------------- |
| **Latencia** | ~2s (overhead SDK)     | ~65ms                 |
| **I/O**      | 0 (estado interno)     | 1R+2W (DynamoDB)      |
| **Coste**    | Mayor tiempo facturado | Menor tiempo, más I/O |



Conclusión
Ambos modelos manejan correctamente errores de dominio sin reintentos innecesarios, pero el tradicional es significativamente más rápido para casos de "fail-fast". 


