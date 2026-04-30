# Phase 1 — Re-execution notes (2026-04-30)

These result logs were re-generated on **2026-04-30** to ensure full
reproducibility against the homologated runtime configuration of the paper.

## Configuration

- **Function**: `fase1-counter-durable`
- **Region**: us-east-2
- **Memory**: 128 MB
- **Runtime**: `python:3.14.DurableFunction.v13`
- **Architecture**: x86_64

## Files

| File | Cold/Warm | Purpose |
|------|-----------|---------|
| `counter_increment_001.txt` | cold | Basic increment operation (Table 1 row "increment") |
| `counter_decrement_001.txt` | cold | Basic decrement operation (Table 1 row "decrement") |
| `counter_get_value_001.txt` | warm | Read operation (Table 1 row "get_value") |
| `counter_latency_baseline_001.txt` | cold | Warm-start baseline @ v=1 |
| `counter_latency_v100_001.txt` | cold | Checkpoint growth @ v=101 (0.029 KB) |
| `counter_fail_once_001.txt` | cold + warm | Transient failure + retry |
| `counter_fail_always_001.txt` | (6 invocations) | Permanent failure: 6 attempts |
| `counter_concurrent_001.txt` | cold | Single concurrent run (single execution context) |
| `counter_replay_observation_001.txt` | cold | Long-running operation (sleep=30s) |

## Cold start range observed (n=7)

575 – 808 ms (mean ≈ 715 ms)

## Warm start observed

263 – 544 ms

## Checkpoint size

- v=1: 0.025 KB
- v=101: 0.029 KB
- Growth: 0.004 KB over 100 operations (effectively constant)

## Failure backoff calendar (this run, v13)

attempts 1→2→3→4→5→6 spaced by approximately 2s, 9s, 17s, 27s, 33s.

This calendar differs from previous measurements with the same SDK
version (e.g., 5-8-17-7-10s observed on 22-Apr-2026 with v13, and
10-12-23-60-87s reported with v12), confirming that the durable runtime
retry algorithm is **not strictly deterministic**.
