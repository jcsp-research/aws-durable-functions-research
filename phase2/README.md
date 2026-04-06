# Fase 2: Pipeline de Codificación de Video con AWS Lambda Durable Functions

**Proyecto de Investigación:** Serverless Durable Functions  
**Autor:** Julio Siguenas Pacheco  
**Fecha:** 2026-04-06  
**Contexto:** WOSC 2026 / Doctorado en Informática  

---

## Resumen Ejecutivo

Esta fase implementa y valida un pipeline de procesamiento de video de 4 etapas utilizando **AWS Lambda Durable Functions (Preview)**. El objetivo es evaluar la capacidad del SDK para manejar flujos de trabajo stateful complejos con tolerancia a fallos, comparando el comportamiento ante errores transitorios, permanentes y de dominio.

**Hallazgo Principal:** El sistema demuestra una diferenciación efectiva entre errores de dominio (irrecuperables) y fallos transitorios (recuperables), logrando una **reducción del 98% en latencia** para casos de validación fallida (de ~3 minutos a 2.8 segundos) mediante el patrón *Fail-Fast*.

---

## Arquitectura del Pipeline


┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌───────────┐
│ initialize_job  │────▶│ validate_video│────▶│ split_video │────▶│ encode_chunk │────▶│ merge_video│
│   (crear ID)    │     │(check formato)│     │(dividir N)  │     │   (N veces)  │     │(ensamblar) │
└─────────────────┘     └──────────────┘     └─────────────┘     └──────────────┘     └───────────┘
│                       │                      │                    │                  │
▼                       ▼                      ▼                    ▼                  ▼
DynamoDB                DynamoDB               DynamoDB             Simulación        DynamoDB
(job state)             (validación)           (chunks)             (CPU sleep)       (final)



**Características implementadas:**
- ✅ Checkpointing automático entre etapas
- ✅ Inyección de fallos controlada (`fail_mode`: none/once/always)
- ✅ Retry automático con backoff exponencial
- ✅ Circuit breaker (límite de 5 reintentos)
- ✅ Fail-fast para errores de dominio
- ✅ Métricas estructuradas por step

---

## Matriz de Experimentos

Se ejecutaron 4 escenarios de prueba cubriendo el espectro completo de comportamientos del sistema:

| ID | Escenario | Estado | Duración | Reintentos | Costo* | Observación |
|----|-----------|--------|----------|------------|--------|-------------|
| `video_happy_path_001` | Flujo nominal | ✅ Succeeded | 10.0s | 0 | $0.000026 | Baseline funcional (10 chunks) |
| `vid_enc_fail_once_001` | Fallo transitorio | ✅ Succeeded | 48.2s | 6 | $0.000105 | Recuperación 100% efectiva |
| `vid_merge_fail_always_001` | Fallo permanente | ❌ Failed** | 3m 30s | 5 | $0.000051 | Circuit breaker validado |
| `video_invalid_format_001` | Error de dominio | ⚠️ 400 Bad Request | 2.8s | **0** | $0.000009 | **98% más rápido*** |

*\*Costos estimados: Lambda (128MB) + DynamoDB (on-demand) en us-east-2*  
*\*\*Fallo esperado y correcto - valida protección ante errores permanentes*  
*\*\*\*Comparado con versión sin clasificación de errores (3 min vs 2.8s)*

### Detalle de Hallazgos

#### 1. Tolerancia a Fallos Transitorios
Cuando se simula un fallo temporal en la codificación de chunks (`fail_mode: once`), el SDK automáticamente reintenta la operación. Se observó:
- **Recuperación:** 100% (6/6 chunks recuperados)
- **Overhead:** +38 segundos (79% más lento que happy path)
- **Costo:** 4× superior al caso nominal (debido a re-ejecuciones parciales)

#### 2. Circuit Breaker (Protección de Costos)
Ante un fallo permanente en la etapa de merge (`fail_mode: always`), el sistema:
- Ejecuta exactamente **5 reintentos** con backoff exponencial (~8s, 13s, 22s, 58s)
- **Preserva el progreso:** Los 3 chunks codificados permanecen en S3/DynamoDB
- **Evita loops infinitos:** Costo acotado a ~$0.000051 vs potencialmente infinito

#### 3. Clasificación de Errores (Innovación)
Se identificó que el SDK no distingue entre excepciones de dominio (irrecuperables) y fallos transitorios. Se implementó el patrón **Result/Either**:

```python
# Errores de dominio -> Return value (no retry)
return {"is_valid": False, "error_type": "domain_validation"}

# Fallos transitorios -> Exception (trigger retry)
raise RuntimeError("Network timeout")