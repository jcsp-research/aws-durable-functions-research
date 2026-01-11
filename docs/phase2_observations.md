# Phase 2 Observations: Stateful Video Encoding Pipeline (Pre-AWS)

## 1. Objective and Scope

The objective of Phase 2 is to evaluate **durable execution** in a realistic,
long-running, stateful workflow: a video encoding pipeline.

Compared to the counter in Phase 1, video encoding introduces:
- multi-step orchestration,
- explicit intermediate state,
- parallelizable computation,
- and failure recovery across long-running tasks.

This phase focuses on **workflow structure, state coordination, and failure semantics**
rather than raw performance, as execution is validated locally prior to AWS deployment.

---

## 2. Pipeline Design Overview

### 2.1 Workflow Structure

The pipeline consists of four logical stages:

1. **Validation**  
   Verify video metadata and basic constraints.

2. **Chunking**  
   Divide the video into fixed-size segments (1-second chunks).

3. **Encoding**  
   Encode each chunk independently. This stage is parallelizable.

4. **Assembly**  
   Reassemble encoded chunks into a final output video.

Each stage is implemented as one or more **durable steps**, designed to be
checkpointed and replayed by the durable execution runtime.

---

## 3. Durable-Oriented Implementation

### 3.1 Step-Based Decomposition

Each logical unit of work is expressed as a deterministic step:
- `validate_video`
- `chunk_video`
- `encode_chunk`
- `assemble_video`

Steps are invoked via `context.step(fn, *args)`, ensuring compatibility with
checkpoint-and-replay semantics.

Intermediate state (e.g., chunk lists, encoded outputs) is passed explicitly
between steps but does not require external storage.

---

### 3.2 Parallelism Model

The encoding stage is structured to support parallel execution:

- Each chunk is encoded independently.
- The pipeline is written to use `context.map()` or `context.parallel()` when
  available in the runtime.
- A sequential fallback is used for local execution.

This design mirrors serverless parallelism patterns used in systems such as
ExCamera, while avoiding explicit coordination logic.

---

## 4. Local Execution Confirmation

### 4.1 Simulated Durable Context

Before deploying to AWS, the pipeline was validated using a simulated execution
context (`FakeContext`) that mimics:

- step invocation,
- sequential ordering,
- and error propagation.

Although this context does not implement checkpointing or replay, it allows
validation of:
- control flow correctness,
- state propagation,
- and deterministic behavior.

---

### 4.2 End-to-End Validation

Local execution confirms that:
- videos are correctly chunked into the expected number of segments,
- each chunk is processed exactly once in the success case,
- the final assembly step produces an ordered result,
- intermediate state is preserved across the pipeline.

Automated tests verify:
- correctness of the number of chunks,
- deterministic ordering in the final output,
- failure behavior when encoding always fails.

---

## 5. Failure Injection and Recovery (Local Simulation)

To study failure semantics, the encoding step supports a configurable
failure rate (`fail_rate`).

Observed behaviors:
- transient failures propagate as exceptions,
- retries can be simulated locally by re-invoking failed steps,
- persistent failures correctly abort the pipeline.

While local retries do not reproduce full replay semantics,
the pipeline structure is compatible with AWS durable execution,
where completed steps would be replayed from checkpoints.

---

## 6. Comparison with Traditional Serverless Pipelines

Even without AWS metrics, qualitative differences are apparent.

### Durable-Oriented Pipeline
- State is implicit in the execution context
- No external coordination store is required
- Failure recovery is declarative
- Control flow is linear and readable

### Traditional Serverless Pipeline
- State must be stored explicitly (e.g., DynamoDB, S3)
- Coordination logic is manual
- Partial failures require explicit recovery handling
- Code complexity increases significantly

These differences motivate a deeper baseline comparison in subsequent work.

---

## 7. Limitations of Pre-AWS Evaluation

This phase does not yet evaluate:
- actual parallel execution at scale,
- real checkpoint and replay overhead,
- end-to-end latency under failure,
- cost per encoded minute of video.

These aspects will be evaluated once the pipeline is deployed
using AWS Lambda Durable Functions.

---

## 8. Summary of Phase 2 Findings

Phase 2 demonstrates that durable execution provides a natural abstraction
for complex, stateful workflows such as video encoding pipelines.

Key observations:
- Durable steps map cleanly to pipeline stages
- State management is significantly simplified
- Parallelism can be expressed declaratively
- The design aligns closely with actor-like coordination models

This phase sets the foundation for quantitative evaluation and
baseline comparison in a real AWS environment.
