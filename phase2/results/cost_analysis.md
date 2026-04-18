
---

#### 2. `phase2/results/cost_analysis.md` (Obligatorio para requisito 2.4)

```markdown
# Análisis de Coste Phase 2: Durable vs Traditional

**Video de referencia:** 95 segundos (1.58 minutos)  
**Precios AWS us-east-2 (abril 2026):**
- Lambda: $0.0000166667/GB-segundo (3008 MB = 2.9375 GB)
- DynamoDB: $1.25/millon write, $0.25/millon read

## Cálculos Detallados

### Durable (video_happy_path_001)
- Billed duration: ~11 segundos
- Memoria: 3008 MB (2.9375 GB)
- Costo Lambda: 11s × 2.9375 GB × $0.0000166667 = **$0.000539**
- DynamoDB: 0 operaciones
- **Total por ejecución:** $0.000539
- **Costo por minuto video:** $0.000539 ÷ 1.58 min = **$0.00034/min**

### Traditional (video_happy_path_001)
- Billed duration: ~6.8 segundos (incluye init 581ms)
- Memoria: 3008 MB (2.9375 GB)  
- Costo Lambda: 6.8s × 2.9375 GB × $0.0000166667 = **$0.000333**
- DynamoDB: 39 operaciones (25 reads + 14 writes)
  - Writes: 14 × $1.25/1M = $0.0000175
  - Reads: 25 × $0.25/1M = $0.00000625
  - Total DDB: **$0.000024**
- **Total por ejecución:** $0.000357
- **Costo por minuto video:** $0.000357 ÷ 1.58 min = **$0.00023/min**

## Resumen Comparativo

| Modelo | Costo/Exec | Costo/Min Video | Overhead vs Optimal |
|--------|------------|-----------------|---------------------|
| **Durable** | $0.000539 | **$0.00034/min** | +51% |
| **Traditional** | $0.000357 | **$0.00023/min** | Base |

## Trade-off Económico
- Durable es **51% más caro** por minuto de video procesado
- Durable elimina costos de DynamoDB (capacidad y operacional)
- Durable simplifica código (menos líneas, menos bugs)