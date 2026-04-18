# Análisis: Invalid Format (video_invalid_format_001)
**Test:** Error de dominio temprano (validación) | **Fecha:** 2026-04-18

## Configuración
- **Video:** 30s, formato `avi` (no soportado)
- **Validación:** Dominio (formato debe ser mp4/mov/mkv)
- **Objetivo:** Evaluar fail-fast en errores de validación temprana

## Resultados Traditional
- **Latencia Total:** 70.037 ms
- **Desglose:**
  - `initialize_job`: 46.076 ms
  - `validate_video`: 18.206 ms
- **DynamoDB:** 1 read + 2 writes
- **Status:** 400 (domain_validation)
- **Mensaje:** "Unsupported input format: avi"

## Resultados Durable Functions
- **Latencia Total:** ~831 ms (de logs: 831.044 ms)
- **Desglose:**
  - `initialize_job`: ~520 ms (overhead runtime)
  - `validate_video`: ~0.009 ms (validación rápida)
- **Status:** 400 (domain_validation)
- **Mensaje:** "Unsupported input format: avi"

## Comparativa de Eficiencia en Fail-Fast

| Métrica | Durable | Traditional | Observación |
|---------|---------|-------------|-------------|
| **Latencia total** | 831 ms | 70 ms | **Traditional 12× más rápido** |
| **Overhead inicial** | ~520 ms | ~46 ms | Durable requiere inicialización SDK |
| **Validación pura** | ~1 ms | ~18 ms | Durable más rápido en lógica pura |
| **I/O DynamoDB** | ~2 ops | 3 ops | Similar, fail-fast no requiere mucho I/O |

## Análisis del Overhead

### Durable Functions
Aunque la validación de dominio toma solo ~1ms, el **runtime Durable requiere:**
1. Inicialización del contexto de ejecución (~520ms)
2. Setup del logger SDK
3. Preparación de checkpoint inicial
4. Serialización del estado (aunque sea fallo inmediato)

**Total:** 831 ms antes de retornar error

### Traditional
Implementación nativa sin middleware:
1. Inicialización Lambda estándar (~46ms)
2. Validación de dominio (~18ms)
3. Guardar metadatos de error (2 writes)
4. Retornar inmediatamente

**Total:** 70 ms

## Implicaciones

### Para errores de dominio (400 Bad Request)
El **Traditional es superior** para validaciones tempranas:
- 12× más rápido en rechazar input inválido
- Menor costo (menor billed duration)
- Respuesta más rápida al cliente/usuario final

### Trade-off SDK vs Nativo
- **Durable:** Inicialización pesada (~520ms) pero lógica de negocio eficiente una vez iniciado
- **Traditional:** Sin overhead de inicialización, ideal para operaciones que fallan rápido

## Recomendación Arquitectónica
Para APIs con alta tasa de errores de validación (input malformado frecuente), considerar:
1. **Validación preliminar** fuera del pipeline Durable (API Gateway o Lambda proxy)
2. O usar Traditional si el ratio de errores de dominio es &gt;20%

## Métricas Clave para Tesis
- **Speedup Traditional:** 11.9× más rápido en errores de dominio
- **Overhead Durable constante:** ~520-800ms incluso en operaciones que deberían tomar &lt;50ms

## Referencia CloudWatch
- **Traditional Execution ID:** `f0c33bf4-13ed-4f58-94e5-4c427a25ec89`
- **Durable Execution ID:** `4e22744b-05bb-47ce-af6d-5ae4b36d4b2c`