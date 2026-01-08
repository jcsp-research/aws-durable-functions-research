# Phase 1 Observations: Stateful Counter with Durable Execution

## 1. Objective and Scope

The goal of Phase 1 is to understand the fundamentals of **durable execution** in AWS Lambda
through the implementation of a minimal yet representative stateful application: a counter.

The counter serves as a canonical example for evaluating:
- state persistence without external storage,
- ordering and atomicity guarantees,
- failure handling via checkpoint-and-replay,
- and the suitability of durable functions as an actor-like abstraction.

This phase focuses on correctness, semantics, and developer experience rather than scalability.

---

## 2. Counter Design Overview

### 2.1 Functional Requirements

The counter supports the following operations:
- `increment(amount)`
- `decrement(amount)`
- `get()`

Operations can be invoked individually or as a **batch of sequential commands**, allowing
explicit evaluation of ordering guarantees.

### 2.2 Durable Implementation

The durable version is implemented using AWS Lambda Durable Functions primitives:
- Each logical operation is modeled as a **durable step**
- State transitions are expressed via `context.step(fn, *args)`
- The counter value is carried forward implicitly by the durable execution context

Conceptually, the counter behaves as a **single-threaded stateful entity**.

### 2.3 Baseline Implementation

The baseline implementation uses:
- AWS Lambda (stateless compute)
- DynamoDB as an explicit external state store

All state reads and updates are performed manually, requiring explicit handling of:
- atomic updates,
- serialization,
- and error conditions.

---

## 3. Local Validation (Pre-AWS)

Although durable execution semantics are enforced by the AWS runtime, we validated the
**logical correctness** of the counter locally using a simulated execution context.

### 3.1 FakeContext for Local Execution

A `FakeContext` was introduced to simulate `context.step()` locally. While it does not
implement checkpointing or replay, it allows validation of:
- step sequencing,
- state propagation,
- and error handling paths.

### 3.2 Automated Test Suite

A pytest-based test suite was implemented and executed locally.

Validated properties include:
- **Sequential ordering** of batch operations
- **Correctness** of state transitions
- **Deterministic behavior** under repeated execution
- **Failure injection**, using a deliberately flaky step

All tests pass deterministically in the local environment.

---

## 4. Checkpoint-and-Replay: Expected Runtime Behavior

Although replay cannot be observed locally, the durable implementation is structured
to rely on the following AWS guarantees:

- Each completed step is **checkpointed**
- On failure, execution is **replayed from the beginning**
- Completed steps return cached results
- Only incomplete steps are re-executed

This design avoids recomputation and eliminates the need for explicit state persistence.

We expect to observe:
- Reduced cost during idle waits
- Transparent recovery from transient failures
- Deterministic re-execution behavior

---

## 5. Ordering and Atomicity Semantics

The counter processes all operations **sequentially**, even when invoked concurrently.

This matches the classical actor model assumption:
- one message processed at a time,
- no shared mutable state,
- implicit serialization of state transitions.

Local batch execution confirms that:
- operations are applied strictly in order,
- intermediate reads observe consistent state,
- no interleaving is possible within a single execution.

---

## 6. Comparison with Baseline Approach

Even without runtime metrics, qualitative differences are evident:

### Durable Execution
- State is implicit and local to the execution
- No explicit serialization or storage logic
- Failure handling is delegated to the runtime
- Control flow is linear and easy to reason about

### Lambda + DynamoDB
- State must be explicitly read and written
- Error handling logic is more complex
- Partial failures require manual recovery logic
- Code complexity increases significantly

These differences are expected to translate into
both performance and cost differences in AWS.

---

## 7. Limitations and Open Questions

Current limitations of this phase include:
- Lack of real checkpoint and replay measurements
- No concurrency stress testing
- No cost data from AWS billing

These limitations will be addressed in subsequent phases.

---

## 8. Summary of Phase 1 Findings

Phase 1 demonstrates that durable execution enables a clean and intuitive model for
stateful serverless programming.

Key takeaways:
- Durable functions naturally model stateful entities
- Sequential semantics align closely with actor systems
- Developer complexity is significantly reduced
- Local validation is possible even without AWS access

Phase 2 will extend these insights to a more complex, parallel workload.

