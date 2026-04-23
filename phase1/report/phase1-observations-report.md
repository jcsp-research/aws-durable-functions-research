# Phase 1 Observations Report: Stateful Counter with AWS Lambda Durable Functions

**Function:** `fase1-counter-durable`  
**Runtime:** Python 3.14.DurableFunction (v12 initial measurements, v13 for reproduction on 2026-04-22) | 128 MB | us-east-2  
**SDK:** aws_durable_execution_sdk_python v12 → v13  
**Dates:** April 2026 (initial); 2026-04-22 (full re-execution with instrumented code)

> This report documents the observations from Phase 1 (counter with state).
> For traceability from each paper claim to its supporting log file, see
> [`TRACEABILITY.md`](TRACEABILITY.md).

---

## 1. Durable Execution Mechanism

AWS Lambda Durable Functions extend the standard Lambda runtime with a
checkpoint-and-replay model. Each step decorated with `@durable_step` and
invoked via `context.step()` persists its result to an internal SDK-managed
store (separate from the application's DynamoDB) upon successful completion.

On re-invocation (after a Lambda timeout, transient error, or explicit retry),
the runtime replays the execution history: steps with a recorded result return
the cached value without re-executing the function body. Only the first
incomplete step triggers actual re-execution.

The `execution_name` parameter acts as the idempotency key. A key
methodological finding of this work is that the `execution_name` is managed
internally by the SDK and **cannot be injected externally** via the Lambda
console or CLI invoke — this limits the verification of idempotency from
outside the SDK (see §2.6).

---

## 2. Key Observations

### 2.1 Checkpoint-and-Replay Verification

Observed directly in `counter_replay_observation_001` (sleep=70 s, Lambda
timeout=60 s):

| Event | Step | Action |
|-------|------|--------|
| 2–3   | initialize_counter | StepStarted + StepSucceeded (checkpointed) |
| 4     | apply_counter_operation | StepStarted — sleep begins |
| 5–13  | InvocationCompleted | 9 Lambda timeouts, automatic SDK retries |
| 14    | — | Final propagation: `Task timed out` |
| —     | initialize_counter | **Never re-executed** across any retry |

**Finding:** in 9 Lambda invocations, `initialize_counter` executed
**exactly once** (first invocation only). The 8 subsequent retries replayed
its cached result from the checkpoint without re-invoking the function.
This is direct empirical evidence of the checkpoint-and-replay guarantee.

Cross-referenced evidence:
- `cloudwatch/2026-04-22/10b_counter_replay_observation_001_sleep70_9retries.csv`:
  `step_invocation: initialize_counter` metric appears in invocation 1 only;
  `step_invocation: apply_counter_operation` appears in all 9 invocations.
- AWS Console Event History (14 events): `StepSucceeded` for
  `initialize_counter` appears once (event 3), followed by 9 `InvocationCompleted`.

The same guarantee was observed via error injection in `counter_fail_once_001`
(transient failure → retry → `initialize_counter` not re-executed) and in
`counter_fail_always_001` (6 retries → `initialize_counter` executed once).

### 2.2 Latency Metrics

Measurements published in the paper (§4.1, Table 1):

| Operation      | exec_ms | billed_ms | init_ms | ckpt_KB |
|----------------|---------|-----------|---------|---------|
| increment      | 788     | 1883      | 746     | 0.025   |
| decrement      | 800     | 2608      | 1474    | 0.025   |
| get_value      | 745     | 1859      | 769     | 0.025   |
| warm           | 596     | 823       | —       | 0.025   |

Cold start overhead: 746–1474 ms billed. Warm invocation: 823 ms
(single-digit-millisecond per-step compute, billed dominated by Lambda
minimum).

**Reproduction on 2026-04-22** (instrumented code, SDK v13) produced
consistent results within ±7%:
- increment: 732 / 1874 / 799 ms
- decrement: 754 / 2464 / 1376 ms
- baseline cold: 729 / 2409 / 1343 ms

This variability is consistent with the well-known variance of Lambda cold
start times.

### 2.3 Checkpoint Size — Effectively Constant

| Version | ckpt_KB | Source |
|---------|---------|--------|
| v=1     | 0.025   | `cloudwatch/2026-04-22/04b_counter_latency_baseline_001_cold.csv` |
| v=101   | 0.029   | `cloudwatch/2026-04-22/05_counter_latency_v100_001.csv` |

The SDK serializes only the current execution context, not the full counter
state history. Growth is negligible (0.004 KB over 100 increments),
confirming that the checkpoint mechanism is constant-size in this application.

### 2.4 Replay Overhead Quantification

Measured in `counter_replay_overhead_001.txt` by comparing step execution
times in cold vs. warm (replayed) invocations:

| Step                    | Cold (ms) | Warm / replayed (ms) | Speedup |
|-------------------------|-----------|----------------------|---------|
| initialize_counter      | 0.377     | 0.112                | 3.4×    |
| apply_counter_operation | 4.875     | 0.296                | 16.5×   |
| build_response          | 3.039     | 0.154                | 19.7×   |

Replay overhead per step is sub-millisecond in a warm container. The
dominant cost is Lambda cold start, not the durable replay mechanism itself.

### 2.5 Retry and Backoff — Not Strictly Deterministic

`counter_fail_always_001` injects a permanent failure in
`apply_counter_operation`. The SDK performs 6 invocations before propagating
`CallableRuntimeError`. The backoff schedule varies between executions:

| Measurement | SDK | Backoff schedule (s)     |
|-------------|-----|--------------------------|
| April 2026  | v12 | 10 → 12 → 23 → 60 → 87   |
| 2026-04-22  | v13 | 5 → 8 → 17 → 7 → 10      |

**Finding:** the retry algorithm is not strictly deterministic across SDK
versions (and possibly even between individual runs). This is documented in
§4.1 of the paper.

A third scenario, `counter_replay_observation_001` with timeout-based retries,
produced a different retry count: **9 retries** before propagating
`Task timed out`. The number of retries depends on the type of error
(exception vs timeout).

### 2.6 Concurrency — Isolation, Not Serial Ordering

Three concurrent invocations of the same payload (`counter_concurrent_001`,
launched in parallel via three console tabs in rapid succession) produced:

- **3 distinct `execution_name` values** — each invocation initiates an
  independent durable execution.
- **3 complete pipeline executions** (3 × 3 `step_invocation` metrics).
- **All returning `counter_value: 1, version: 1`** — no shared state.

This is consistent with per-invocation isolation, but contradicts the
classical actor semantics of serial FIFO processing on a persistent logical
entity (as in Azure Durable Entities). AWS Lambda Durable Functions
implements **isolated workflow orchestration**, not persistent stateful
entities. Coordination across concurrent invocations is the programmer's
responsibility (see paper Table 4 for full comparison).

### 2.7 Idempotency — Methodological Limitation

Two sequential invocations with identical payload produced distinct
`execution_name` values:

- Execution 1: `2e375825-f00d-459c-851a-1a2e13ec8f7a`
- Execution 2: `fd2aadf9-c3d3-4d32-92ed-4dd43c80910c`

**Finding:** the Lambda console and CLI-based Invoke generate a fresh
`execution_name` per invocation; the SDK-level idempotency cache (which
returns cached results for repeated `execution_name`) **cannot be
triggered externally**. Idempotency is therefore verified **indirectly**
via the `fail_once` scenario, where the SDK's automatic retry reuses the
internal `execution_name`, and we observe that `initialize_counter` is
not re-executed.

---

## 3. Unexpected Behaviours and Limitations

1. **`context.parallel()` non-functional:** confirmed broken in Phase 2
   (`SerDesError: Unsupported type: function`). Not applicable to Phase 1,
   but documented as a platform limitation affecting Phase 2 design.

2. **Fragmented observability:** each durable execution spans multiple
   Lambda invocations with separate CloudWatch log streams. There is no
   single log entry covering the total billed duration of a durable
   execution — cost attribution requires correlating streams by
   `execution_name`.

3. **Cold start overhead dominant for short workflows:** counter has 3
   steps totaling ~5 ms of real work. Cold start (746–1474 ms) represents
   40–60% of total billed duration. In this regime, the cost comparison
   vs. a traditional Lambda+DynamoDB approach is uninformative: cold start
   dominates in both. The meaningful cost comparison is presented in
   Phase 2 (§4.2 of the paper) with the video encoding pipeline.

4. **External `execution_name` injection not supported:** as noted in §2.7,
   this limits external verification of the idempotency cache.

5. **Backoff schedule non-deterministic:** varies between SDK versions
   and possibly between individual runs (§2.5).

6. **Retry count depends on error type:** exceptions → 6 retries; timeouts
   → 9 retries (observed on 2026-04-22).

---

## 4. Artefacts

### Original test results (results/)

| File | Description |
|------|-------------|
| `results/counter_increment_001.txt` | Increment — baseline metrics |
| `results/counter_fail_once_001.txt` | Transient failure + transparent retry |
| `results/counter_fail_always_001.txt` | Permanent failure — 6-attempt backoff (SDK v12) |
| `results/counter_replay_observation_001.txt` | Direct replay observation |
| `results/counter_idempotency_001.txt` | Idempotency verification |
| `results/counter_latency_baseline_001.txt` | Warm start baseline |
| `results/counter_latency_v100_001.txt` | Checkpoint size at version=101 |
| `results/counter_concurrent_001.txt` | Concurrency isolation test |
| `results/counter_replay_overhead_001.txt` | Per-step replay overhead |

### Initial CloudWatch exports (cloudwatch/)

| File | Description |
|------|-------------|
| `cloudwatch/cloudwatch_counter_fail_once_001.csv` | Raw CloudWatch export |
| `cloudwatch/cloudwatch_counter_fail_always_001.csv` | Raw CloudWatch export (6 invocations, SDK v12) |
| `cloudwatch/cloudwatch_counter_idempotency_001.csv` | Raw CloudWatch export |
| `cloudwatch/cloudwatch_counter_concurrent_001.csv` | Raw CloudWatch export |

### Re-execution with instrumented code (cloudwatch/2026-04-22/)

Full re-execution on 2026-04-22 with an updated `lambda_function.py` that
emits two new structured metrics:

- **`invocation_attempt`**: per-container invocation counter with a heuristic
  `is_likely_replay` flag (based on seconds since module load).
- **`step_invocation`**: per-step execution metric — by presence/absence in
  a retry, it directly evidences checkpoint replay.

See `cloudwatch/2026-04-22/README.md` for the full 17-file listing and
per-test notes.

### Code

- `code/lambda_function.py`: current instrumented version deployed on AWS.
- `code/archive/lambda_function_pre_20260422.py`: previous version, used
  to generate the 4 CSVs in `cloudwatch/` (top level).
