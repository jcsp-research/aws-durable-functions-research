# Phase 2 — Video Pipeline Evaluation (Local)

This document reports the experimental evaluation of the video encoding workflow
implemented using:

- **Durable execution** (`video_pipeline`)
- **Explicit-state baseline** (`video_baseline` with MemoryStore)

The goal is to quantify coordination overhead, execution cost proxies, and
workflow complexity in both models.

---

## Experimental Setup

The workload encodes a synthetic 10-second video, split into 1-second chunks
(10 chunks total). Each chunk is independently encoded and later assembled.

### Durable Execution
- Orchestration via `context.step(...)`
- State persisted implicitly via checkpoint-and-replay
- No external storage for workflow state

### Baseline Execution
- Explicit job and chunk state stored in `MemoryStore`
- Manual retries and status polling
- State accessed via `get_job`, `update_job`, `get_chunk`, etc.

### Metrics Collected
For each run, we record:

| Column | Meaning |
|-------|--------|
| `time_ms` | End-to-end local runtime |
| `store_ops` | Total number of state-store operations |
| `retries` | Proxy for retry overhead (currently 0 in these runs) |
| `n_chunks` | Number of encoded chunks |

All raw measurements are stored in:


