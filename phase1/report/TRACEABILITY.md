# Trazabilidad Fase 1 — Datos del Paper → Logs

Mapeo de cada afirmación numérica del paper WOSC 2026 (§4.1) al log CSV
o fichero de resultado que la soporta en este repositorio.

---

## Organización de la evidencia

```
phase1/
├── cloudwatch/
│   ├── cloudwatch_counter_concurrent_001.csv   ← tanda inicial (código antiguo)
│   ├── cloudwatch_counter_fail_always_001.csv
│   ├── cloudwatch_counter_fail_once_001.csv
│   ├── cloudwatch_counter_idempotency_001.csv
│   └── 2026-04-22/                             ← re-ejecución con código instrumentado
│       ├── README.md                           ← descripción de esta tanda
│       ├── 01_counter_increment_001.csv
│       └── ... (17 CSVs)
├── code/
│   ├── lambda_function.py                      ← versión instrumentada actual
│   └── archive/
│       └── lambda_function_pre_20260422.py    ← versión antigua (para reproducir los 4 CSVs del nivel superior)
├── report/
│   ├── phase1-observations-report.md           ← informe de observaciones
│   └── TRACEABILITY.md                         ← este fichero
├── results/                                    ← 8 .txt con resultados originales del paper
└── test-events/                                ← 10 JSONs cargables en consola Lambda
```

---

## Tabla 1 — Latencia Fase 1 (ms)

Datos del paper en §4.1 Tabla 1:

| Operación  | exec_ms | billed_ms | init_ms | ckpt_KB | Log soporte (primario)                       |
|------------|---------|-----------|---------|---------|----------------------------------------------|
| increment  | 788     | 1.883     | 746     | 0,025   | `results/counter_increment_001.txt`          |
| decrement  | 800     | 2.608     | 1.474   | 0,025   | `results/counter_increment_001.txt` (+ decrement variante) |
| get_value  | 745     | 1.859     | 769     | 0,025   | `results/counter_get_value_001.txt`          |
| caliente   | 596     | 823       | —       | 0,025   | `results/counter_replay_overhead_001.txt` invocación 2 |

**Validación cruzada 22 abril 2026** (reproducción independiente):
- `cloudwatch/2026-04-22/01_counter_increment_001.csv` → 732 / 1.874 / 799 ms (±7% vs paper).
- `cloudwatch/2026-04-22/02a_counter_decrement_001.csv` → 754 / 2.464 / 1.376 ms (±5% vs paper).
- `cloudwatch/2026-04-22/04b_counter_latency_baseline_001_cold.csv` → 729 / 2.409 / 1.343 ms.

---

## §4.1 — Afirmaciones textuales del paper

### "Cold start añade 746–1.474 ms de sobrecoste facturado"

- Mínimo 746 ms: `results/counter_increment_001.txt`.
- Máximo 1.474 ms: `results/counter_increment_001.txt` (sección decrement).

### "Invocación en caliente factura solo 823 ms"

- `results/counter_replay_overhead_001.txt` invocación 2 (warm).

### "Checkpoint prácticamente constante: 0,025 KB en version=1 y 0,029 KB en version=101"

- **v=1 → 0,025 KB**: `cloudwatch/2026-04-22/04b_counter_latency_baseline_001_cold.csv`
  (mensaje con `"size_kb": 0.025, "state_version": 1`).
- **v=101 → 0,029 KB**: `cloudwatch/2026-04-22/05_counter_latency_v100_001.csv`
  (`"size_kb": 0.029, "state_version": 101`).

### "El sobrecoste de replay por paso es sub-milisegundo en container caliente (0,112 / 0,296 / 0,154 ms); speedup 3,4× a 19,7× según el paso"

- Medición caliente: `results/counter_replay_overhead_001.txt` invocación 2.
- Medición en cold start (0,4–4,9 ms): `results/counter_replay_overhead_001.txt` invocación 1.

---

## Escenario `fail-once`

### "apply_counter_operation falla en el primer intento y el runtime reintenta automáticamente sin re-ejecutar initialize_counter"

**Log soporte**: `cloudwatch/2026-04-22/06d_counter_fail_once_001_SUCCESS_replay_observed.csv`

Evidencia:
- 2 `platform.start` events.
- Invocación 1: `step_invocation: initialize_counter` + `step_invocation: apply_counter_operation` + error `Simulated transient failure on first attempt`.
- Invocación 2: `step_invocation: apply_counter_operation` (exitosa) + `step_invocation: build_response`. **NO** aparece `initialize_counter`.

Conclusión: `initialize_counter` se reproduce desde checkpoint sin re-ejecutarse.

**Notas de reproducibilidad**:
- Logs `06a/b/c_` son intentos con el marker DynamoDB ya consumido (no dispararon el fallo). Conservados por transparencia metodológica.
- Para reproducir el fallo hay que borrar el marker o cambiar `failure_key` en el JSON. `06d_` usa `failure_key: "phase1-fail-once-counter-DEFENSA-2026-04-22"`.

---

## Escenario `fail-always`

### "Seis intentos con backoff 10→12→23→60→87 s (SDK v12) / 5→8→17→7→10 s (SDK v13)"

- **SDK v12**: `cloudwatch/cloudwatch_counter_fail_always_001.csv` + `results/counter_fail_always_001.txt` (mediciones originales).
- **SDK v13**: `cloudwatch/2026-04-22/07_counter_fail_always_001.csv` (reproducción).

Evidencia en CSV v13:
- 6 `platform.start` events.
- Gaps observados (s entre consecutive `platform.start`): 4,9 / 8,2 / 17,2 / 7,2 / 10,2.
- 6 errores `Simulated permanent failure`.
- `step_invocation: initialize_counter` solo en invocación 1.
- Error final: `CallableRuntimeError`.

---

## Escenario `replay-by-timeout`

### "Nueve intentos antes de propagar Task timed out. initialize_counter se ejecutó exactamente una vez"

**Log soporte**: `cloudwatch/2026-04-22/10b_counter_replay_observation_001_sleep70_9retries.csv`

Configuración: `debug_sleep_seconds: 70`, timeout Lambda 60 s.

Evidencia:
- 9 `platform.start` events.
- 9 `platform.report` con `billedDurationMs: 60000` y `status: timeout`.
- `step_invocation: initialize_counter` solo en invocación 1.
- `step_invocation: apply_counter_operation` en las 9.
- Duración total ejecución durable: 12 min 25 s.
- Execution name: `124cd528-2695-4b77-bb92-c9653bd37819`.

---

## Idempotencia metodológica

### "Dos invocaciones sucesivas con payload idéntico generaron execution_names distintos"

- **Ejecución 1**: `cloudwatch/2026-04-22/08a_counter_idempotency_001.csv` → execution_name `2e375825-f00d-459c-851a-1a2e13ec8f7a`.
- **Ejecución 2**: `cloudwatch/2026-04-22/08a_counter_idempotency_001.csv` (segunda invocación en la misma ventana) → execution_name `fd2aadf9-c3d3-4d32-92ed-4dd43c80910c`.

---

## Concurrencia

### "Tres invocaciones concurrentes produjeron ejecuciones durables independientes con execution_names distintos"

**Log soporte**: `cloudwatch/2026-04-22/09b_counter_concurrent_001_parallel_3x.csv`

Evidencia:
- 3 execution_names distintos:
  - `cfc45a59-8f6a-42eb-b094-0697b3a49ea7`
  - `3f606a4a-f735-42a8-b764-7dd2fea56a8e`
  - `d28dd9da-450c-41ee-b861-d53a739e1785`
- 3 `platform.start` con gaps de 1,70 s y 5,82 s.
- Cada invocación ejecuta su propio pipeline completo (3 `step_invocation` por cada una, 9 en total).
- Cada una termina con `counter_value: 1, version: 1` independientemente.
- Invocación 1: cold (1.413 ms init). Invocaciones 2 y 3: warm (mismo container reutilizado, `invocation_count = 2, 3`).

---

## Capturas de AWS Console

Las siguientes capturas del panel "Durable executions" → Event history
complementan los CSVs y están disponibles bajo demanda:

- **fail_once**: Event history de 11 eventos. `initialize_counter`
  aparece como StepStarted (evento 2) + StepSucceeded (evento 3)
  — una sola vez.
- **replay-by-timeout**: Event history de 14 eventos. `initialize_counter`
  como StepSucceeded una sola vez (evento 3); seguido de 9
  InvocationCompleted (uno por retry por timeout).

---

## Notas de reproducibilidad

1. **Latencia absoluta varía entre cold starts** (716–1.474 ms observados).
   Los valores del paper están dentro del rango de las mediciones archivadas.
2. **Checkpoint exactamente reproducible** (0,025 / 0,029 KB) porque
   depende solo de serialización JSON del estado.
3. **Backoff del SDK no determinista** — véase §4.1 del paper.
4. **Reintentos según tipo de error**:
   - Excepciones (`CallableRuntimeError`) → 6 retries.
   - Timeouts (`Task timed out`) → 9 retries.
