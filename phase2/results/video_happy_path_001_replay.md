# Test Case: video_happy_path_001_replay (Checkpoint Replay Analysis)

**Status:** ✅ Succeeded  
**Execution Date:** 2026-04-18 13:49:07 UTC  
**Duration:** 10.456 segundos  
**Execution Model:** durable_sequential_fallback  

## Comparativa vs Ejecución Original

| Métrica | Original | Replay (mismo job_id) | Δ |
|---------|----------|----------------------|---|
| **Duración** | 10.816s | 10.456s | -3.3% |
| **job_id** | 759aa5a3-ce0a-4fba-9e23-746f87dc3ec0 | (mismo) | - |
| **version** | 3 | 3 | Sin cambio |
| **Chunks** | 10 | 10 | - |

## Insight Crítico: Semántica de Replay

**Observación clave:** A pesar de proporcionar el mismo `job_id` y tener checkpoints previos, el runtime **re-ejecutó todos los steps** (initialize, validate, split, encode, merge).

**Implicación:** El checkpoint-and-replay de AWS Lambda Durable Functions está optimizado para:
- ✅ Recuperación de fallos transitorios **durante** una ejecución activa
- ❌ No para cachear resultados de ejecuciones completadas exitosamente

**Costo:** Cada invocación con el mismo job_id incurre en el mismo coste computacional (~$0.0006 por ejecución).

## JSON Output

```json
{
  "statusCode": 200,
  "body": {
    "message": "fase2-video-durable executed successfully",
    "job_id": "759aa5a3-ce0a-4fba-9e23-746f87dc3ec0",
    "video_id": "video-001",
    "status": "merged",
    "chunk_count": 10,
    "encoded_chunk_count": 10,
    "output_uri": "s3://durable-video-artifacts/final/759aa5a3-ce0a-4fba-9e23-746f87dc3ec0/video-001_encoded.mp4",
    "version": 3,
    "execution_model": "durable_sequential_fallback"
  }
}


Conclusión p
El modelo durable garantiza idempotencia (mismo resultado) pero no memoización (reutilización de resultados previos). Esto es consistente con la semántica de "exactly-once" execution vs "caching".

