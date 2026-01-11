# Phase 2 Comparison: Durable Execution vs. Explicit State Management

## 1. Comparison Objective

This section compares two implementations of a video encoding pipeline:

1. **Durable execution pipeline** (`video_pipeline/`)
2. **Traditional serverless baseline with explicit state** (`video_baseline/`)

Both pipelines implement identical functionality:
- video validation,
- chunking,
- per-chunk encoding,
- final assembly.

The comparison focuses on **state management complexity**, **coordination overhead**, and **fault-handling semantics**, rather than raw performance, which will be evaluated in AWS in later phases.

---

## 2. Architectural Differences

### 2.1 Durable Execution Pipeline

The durable pipeline expresses the workflow as a sequence of deterministic steps:
- state is implicitly maintained by the durable execution runtime,
- completed steps are checkpointed,
- retries and recovery are handled transparently.

The programmer only specifies:
- step boundaries,
- input/output of each step,
- high-level control flow.

No external state store is required for coordination.

---

### 2.2 Baseline Pipeline with Explicit State

The baseline pipeline simulates a traditional serverless architecture using an explicit state store (modeled as an in-memory DynamoDB-like store).

The implementation requires:
- explicit job and chunk schemas,
- manual state transitions,
- retries implemented at the application level,
- polling and aggregation to detect completion.

All coordination logic is implemented by the application.

---

## 3. Code Complexity Comparison

| Aspect                    | Durable Pipeline | Baseline Pipeline |
|---------------------------|------------------|-------------------|
| Workflow expression       | Linear, step-based | Imperative, state-driven |
| External state store      | None             | Required (Jobs + Chunks) |
| Retry logic               | Declarative (runtime) | Manual loops |
| Failure recovery          | Implicit replay  | Explicit reprocessing |
| Coordination logic        | Minimal          | Polling + aggregation |
| Cognitive load            | Low              | High |

Qualitatively, the baseline pipeline requires significantly more boilerplate to express the same workflow semantics.

---

## 4. Quantitative Proxy: State Store Operations

To approximate coordination overhead, the baseline pipeline was instrumented to count state store operations.

### 4.1 Observed Store Operations (10 chunks, no failures)


put_job: 1
get_job: 1
update_job: 4
put_chunks: 1
list_chunks: 4
get_chunk: 20
update_chunk: 20
chunk_status_counts: 2


These operations represent the minimum coordination cost for a successful execution.

In a real AWS deployment, each operation would correspond to a DynamoDB read or write.

---

### 4.2 Interpretation

- Each chunk requires multiple reads and writes even in the success case.
- State transitions (e.g., PENDING → DONE) must be explicitly persisted.
- Coordination requires polling and aggregation to detect pipeline completion.

In contrast, the durable pipeline performs **no explicit external state operations** for coordination; state is managed by the durable runtime.

---

## 5. Failure Handling Implications

When failures are introduced:
- the baseline pipeline increases state store operations proportionally to retries,
- each retry requires additional reads, writes, and status updates,
- complexity grows with failure rate and concurrency.

In the durable pipeline:
- retries are handled by the runtime,
- completed steps are replayed from checkpoints,
- no additional coordination logic is required from the programmer.

This highlights a key advantage of durable execution: **failure handling does not increase application-level complexity**.

---

## 6. Summary of Tradeoffs

| Dimension              | Durable Execution | Explicit State Baseline |
|-----------------------|------------------|-------------------------|
| State visibility      | Implicit (runtime-managed) | Explicit (application-managed) |
| Recovery semantics    | Checkpoint & replay | Manual retries |
| Coordination overhead | Minimal          | High |
| Scalability burden    | Runtime-managed  | Application-managed |
| Suitability for complex workflows | High | Moderate to low |

---

## 7. Implications

This comparison demonstrates that durable execution significantly reduces both:
- the amount of coordination code,
- and the number of external state operations required to implement stateful serverless workflows.

These advantages become increasingly pronounced as workflows grow longer, more parallel, and more failure-prone.

The results motivate further evaluation in a real AWS environment, where cost and latency implications can be measured directly.
