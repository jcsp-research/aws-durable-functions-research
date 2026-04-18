
---

### 3. `phase2/EXPERIMENTS.md` (Registro Maestro)

```markdown
# Phase 2: Video Encoding Pipeline - Experimental Results

**Execution Date:** 2026-04-18  
**Environment:** AWS Lambda (us-east-2), Python 3.13, Durable Functions SDK  

## Test Matrix

| Test Case | Durable Status | Trad Status | Scenario | Chunks |
|-----------|---------------|-------------|----------|--------|
| video_happy_path_001 | ✅ 200 | ✅ 200 | Happy path | 10 |
| vid_enc_fail_once_001 | ✅ 200 | ✅ 200 | Transient recovery | 6 |
| vid_merge_fail_always_001 | ❌ Failed | ❌ 500 | Permanent failure | 3 |
| video_invalid_format_001 | ⚠️ 400 | ⚠️ 400 | Domain validation | 0 |

## Key Findings

### 1. Parallelism Limitations
- **Durable SDK:** `parallel()` y `map()` fallan con `BatchResult` no materializable → fallback secuencial consistente
- **Resultado:** Ambos modelos ejecutan secuencialmente en la práctica (paralelismo no logrado)

### 2. Failure Handling Behavior
- **Transient (fail_once):** Durable reintenta automáticamente (transparente), Traditional reintenta vía código (3 intentos)
- **Permanent (fail_always):** Durable gasta ~63s en reintentos antes de rendirse, Traditional falla en ~2.7s
- **Domain (invalid_format):** Ambos retornan 400 sin reintentos (correcto)

### 3. State Management
- **Durable:** Checkpoint interno (5-6 KB), 0 I/O explícito, versiones estables (v3)
- **Traditional:** DynamoDB explícito (6-13 versiones), 17-25 reads + 6-14 writes por ejecución

### 4. Latency Comparison
| Scenario | Durable | Traditional | Delta |
|----------|---------|-------------|-------|
| Happy path (10 chunks) | 10.8s | 6.2s | +74% |
| With transient failure | 8.25s | 4.04s | +104% |
| Validation failure | 1.99s | 0.065s | +2962% |

### 5. Cost Implications
- **Durable:** Mayor tiempo de ejecución (billed duration) pero sin costos de DynamoDB
- **Traditional:** Menor tiempo pero ~40 operaciones DynamoDB por ejecución exitosa

## Reproducibility

```bash
# Ejecutar tests individuales
aws lambda invoke --function-name phase2-video-durable \
  --payload file://test_events/video_happy_path_001.json output.json

aws lambda invoke --function-name phase2-video-traditional \
  --payload file://test_events/video_happy_path_001.json output.json



  Artifacts Generated
S3 Objects: s3://durable-video-artifacts/encoded/ (chunks procesados)
Logs: CloudWatch Log Groups /aws/lambda/phase2-video-*
Metrics: CloudWatch Logs Insights queries disponibles
