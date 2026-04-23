# Tanda experimental — 22 de abril de 2026

Directorio: `phase1/cloudwatch/2026-04-22/`

Esta subcarpeta contiene los **17 logs de CloudWatch** de la re-ejecución
completa de los 10 tests de Fase 1, ejecutada el 22 de abril de 2026.

## Por qué una subcarpeta fechada

Los 4 CSVs que están en `phase1/cloudwatch/` (nivel superior) fueron
generados con la versión inicial de `lambda_function.py`. Esta tanda de
17 CSVs se generó tras **actualizar el código a la versión instrumentada**
(ver `phase1/code/lambda_function.py` actual vs
`phase1/code/archive/lambda_function_pre_20260422.py`).

La versión instrumentada emite dos métricas nuevas:

- **`invocation_attempt`**: contador de invocaciones por container Lambda,
  con heurística `is_likely_replay` que detecta reutilización de container.
- **`step_invocation`**: una métrica por cada step ejecutado, permitiendo
  verificar qué pasos se ejecutan en retry vs. cuáles se reproducen desde
  checkpoint.

Estas métricas son las que soportan afirmaciones como *"en las nueve
invocaciones observadas, initialize_counter se ejecutó exactamente una vez"*
(ver §4.1 del paper).

## Ficheros

Numerados por orden de aparición del test en el paper:

| Prefijo | Test (JSON en `phase1/test-events/`)               | Hallazgo clave                           |
|---------|----------------------------------------------------|------------------------------------------|
| `01_`   | counter_increment_001                              | Cold start baseline                      |
| `02a_`  | counter_decrement_001                              | Valida Tabla 1                           |
| `02b_`  | counter_decrement_001 (repeat)                     | Variabilidad cold start                  |
| `03_`   | counter_get_value_001                              | Operación idempotente de lectura         |
| `04a_`  | counter_latency_baseline_001 (warm)                | Run caliente, sin init                   |
| `04b_`  | counter_latency_baseline_001 (cold)               | Cold start forzado (mem change 128→129→128) |
| `05_`   | counter_latency_v100_001                           | Checkpoint 0,029 KB en v=101              |
| `06a-c_`| counter_fail_once_001 (marker ya consumido)       | Intentos que no dispararon el fallo      |
| `06d_`  | counter_fail_once_001 (SUCCESS, replay observable)| initialize_counter ejecuta 1/2 invocaciones |
| `07_`   | counter_fail_always_001                            | 6 intentos SDK v13, backoff 5→10 s       |
| `08a_`  | counter_idempotency_001                            | execution_names distintos desde consola  |
| `09a_`  | counter_concurrent_001 (sequential)                | Baseline para comparación concurrencia   |
| `09b_`  | counter_concurrent_001 (parallel 3x)              | 3 execution_names aislados               |
| `10a_`  | counter_replay_observation_001 (sleep 30)         | No dispara timeout (timeout=60s cabe)     |
| `10b_`  | counter_replay_observation_001 (sleep 70)         | **9 intentos, initialize_counter 1/9**   |

## Cómo se generaron

1. Desplegar la versión actual de `phase1/code/lambda_function.py` en AWS
   Lambda (`fase1-counter-durable`, us-east-2, 128 MB, timeout 60 s).
2. En la consola Lambda, cargar el evento JSON correspondiente desde
   `phase1/test-events/`.
3. Pulsar Test.
4. Ir a CloudWatch Logs → log group `/aws/lambda/fase1-counter-durable`.
5. Filtrar por la ventana temporal del test.
6. Usar "Log Events Viewer" → download as CSV.

## Notas específicas

- **06a-c vs 06d**: el marker DynamoDB
  (`phase1-fail-once-counter-001` en tabla `durable-failure-markers`)
  se consume en la primera ejecución exitosa. Para reproducir el fallo
  hay que **borrar el marker** o **cambiar `failure_key`** en el JSON.
  `06d_` usa `failure_key: "phase1-fail-once-counter-DEFENSA-2026-04-22"`.
- **09b_**: concurrencia real lograda lanzando tres "Test" en tres
  pestañas de consola en ráfaga de <2 segundos. Los 3 execution_names
  observados: `cfc45a59...`, `3f606a4a...`, `d28dd9da...`.
- **10b_**: sleep 70 s con timeout 60 s. Execution name
  `124cd528-2695-4b77-bb92-c9653bd37819`. Duración total: 12 min 25 s.
  Las capturas del Event History (14 eventos) complementan este CSV.

## Trazabilidad dato → log

Ver `phase1/report/TRACEABILITY.md` para el mapeo completo de cada
afirmación numérica del paper (§4.1) al fichero CSV que la soporta.
