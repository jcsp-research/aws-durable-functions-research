# Phase 1 Observations Report: Stateful Counter with AWS Lambda Durable Functions

**Function:** `fase1-counter-durable`  
**Runtime:** Python 3.14.DurableFunction.v12 | 128 MB | us-east-2  
**SDK:** aws_durable_execution_sdk_python v12  
**Date:** April 2026

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

The `execution_name` parameter acts as the idempotency key. Re-invoking with
the same `execution_name` after completion returns the cached final result
(default retention: 14 days).

---

## 2. Key Observations

### 2.1 Checkpoint-and-Replay Verification

Observed directly in `counter_replay_observation_001` (16-event history):

| Event | Step | Action |
|-------|------|--------|
| 2–3   | initialize_counter | StepStarted + StepSucceeded (checkpointed) |
| 4     | apply_counter_operation | StepStarted — sleep begins |
| 5–10  | InvocationCompleted (error) | Lambda timeouts, retries |
| ...   | initialize_counter | **Never appears again** — replayed from cache |

**Finding:** `initialize_counter` executed exactly once across all retries.
This is the core guarantee: completed steps are never re-executed.

### 2.2 Latency Metrics

| Operation      | exec_ms | billed_ms | init_ms | ckpt_KB |
|----------------|---------|-----------|---------|---------|
| increment      | 788     | 1883      | 746     | 0.025   |
| decrement      | 740     | 1761      | 679     | 0.025   |
| get_value      | 801     | 2509      | 1384    | 0.025   |
| warm (baseline)| 639     | 831       | —       | 0.025   |

Cold start overhead: 570–1384 ms billed. Warm invocation: 831 ms.

### 2.3 Checkpoint Size — Effectively Constant

| Version | ckpt_KB |
|---------|---------|
| v1      | 0.025   |
| v101    | 0.029   |

The SDK serializes only the current execution context, not the full counter
state history. Growth is negligible (0.004 KB over 100 increments).

### 2.4 Retry and Backoff

Observed in `counter_fail_always_001` — 6 invocations:

| Attempt | billed_ms | Gap to next |
|---------|-----------|-------------|
| 1       | 1572      | ~10 s       |
| 2       | 516       | ~12 s       |
| 3       | 474       | ~23 s       |
| 4       | 473       | ~60 s       |
| 5       | 493       | ~87 s       |
| 6       | 528       | — (propagate CallableRuntimeError) |

Exponential backoff: 10 → 12 → 23 → 60 → 87 s. After 6 attempts the
durable runtime propagates `CallableRuntimeError` to the caller.

### 2.5 Concurrency and Ordering

Concurrent invocations generate **independent durable executions** with
distinct `execution_name` values. Each starts from `value=0` in isolation —
no shared state between executions. Sequential processing within each
execution was verified: `apply_counter_operation` never began before
`initialize_counter` completed and persisted its checkpoint.

This is consistent with full actor encapsulation but implies that
coordination across concurrent executions is the programmer's responsibility.

### 2.6 Idempotency

Two invocations with identical inputs (both returning `counter_value=1,
version=1`) confirmed functional idempotency of the counter logic.
True idempotency for re-invocation with the same `execution_name` is a
durable SDK guarantee verified in the replay scenario.

---

## 3. Unexpected Behaviours and Limitations

1. **`context.parallel()` non-functional:** Not applicable to Phase 1 counter,
   but confirmed broken in Phase 2 (`SerDesError: Unsupported type: function`).

2. **Fragmented observability:** Each durable execution spans multiple Lambda
   invocations with separate CloudWatch log streams. There is no single log
   entry covering the total billed duration of a durable execution — cost
   attribution requires correlating streams by `execution_name`.

3. **Cold start overhead dominant:** For short workflows (counter = 3 steps),
   cold start (570–1384 ms) can represent 40–60% of total billed duration.

---

## 4. Artefacts

| File | Description |
|------|-------------|
| `results/counter_increment_001.txt` | Increment — baseline metrics |
| `results/counter_fail_once_001.txt` | Transient failure + transparent retry |
| `results/counter_fail_always_001.txt` | Permanent failure — 6-attempt backoff |
| `results/counter_replay_observation_001.txt` | Direct replay observation (16 events) |
| `results/counter_idempotency_001.txt` | Idempotency verification |
| `results/counter_latency_baseline_001.txt` | Warm start baseline |
| `results/counter_latency_v100_001.txt` | Checkpoint size at version=101 |
| `results/counter_concurrent_001.txt` | Concurrency isolation test |
| `cloudwatch/cloudwatch_counter_fail_once_001.csv` | Raw CloudWatch export |
| `cloudwatch/cloudwatch_counter_fail_always_001.csv` | Raw CloudWatch export (6 invocations) |
| `cloudwatch/cloudwatch_counter_idempotency_001.csv` | Raw CloudWatch export |
| `cloudwatch/cloudwatch_counter_concurrent_001.csv` | Raw CloudWatch export |
