# Phase 3: Durable Functions and the Actor Model

## 1. Objective

The objective of Phase 3 is to position AWS Lambda Durable Functions within the
broader landscape of **actor-based programming models** for distributed systems.

Building on the implementations from Phase 1 (counter entity) and Phase 2
(video encoding pipeline), this phase analyzes whether durable functions can be
considered actors, how closely they align with classical actor semantics, and
what design tradeoffs arise from serverless constraints.

---

## 2. Actor Model Background

The actor model is a foundational abstraction for concurrent and distributed
computation, characterized by four core properties:

1. **Encapsulation of state**: Each actor owns its private state.
2. **Asynchronous message handling**: Actors interact via message passing.
3. **Sequential message processing**: An actor processes one message at a time.
4. **Fault isolation and recovery**: Actor failures are isolated and recoverable.

Modern actor systems (e.g., Akka, Orleans) extend this model with:
- location transparency,
- automatic activation and passivation,
- persistence and fault tolerance.

---

## 3. Phase 1 Counter as an Actor

### 3.1 Mapping the Counter to Actor Semantics

The durable counter implemented in Phase 1 exhibits a close correspondence to a
classical actor:

| Actor Property | Counter Entity |
|----------------|----------------|
| Identity       | Execution ID |
| State          | Counter value |
| Messages       | increment, decrement, get |
| Processing     | Sequential, ordered |
| Fault recovery | Checkpoint & replay |

Each invocation represents a message to the actor, and the durable execution
runtime guarantees ordered processing and state consistency.

---

### 3.2 Idempotency and Exactly-Once Semantics

Durable execution provides idempotent behavior by caching completed steps and
replaying them during recovery.

From the programmer’s perspective:
- repeated invocations with the same execution ID behave like duplicate messages,
- state transitions are applied exactly once.

This mirrors guarantees offered by persistent actor systems using event sourcing
or write-ahead logging.

---

## 4. Phase 2 Video Pipeline as an Actor System

### 4.1 Orchestration as a Supervising Actor

The video encoding pipeline can be interpreted as a **supervising actor**:

- it maintains global workflow state,
- it spawns logical sub-tasks (chunk encoders),
- it aggregates results and decides when to assemble output.

The durable execution context acts as the supervisor’s mailbox and state store.

---

### 4.2 Chunk Encoders as Logical Actors

Each video chunk encoder behaves like an independent actor:
- it processes a single chunk,
- it maintains local execution state,
- failures are isolated to the chunk level.

Unlike classical actor systems, chunk actors are not long-lived processes but
logical actors whose state is persisted across executions.

This resembles the **virtual actor** model used in systems such as Orleans.

---

## 5. Comparison with Related Systems

### 5.1 AWS Durable Functions vs. Azure Durable Entities

Both AWS and Azure durable systems provide actor-like abstractions:

| Aspect | AWS Durable Functions | Azure Durable Entities |
|------|-----------------------|------------------------|
| State persistence | Checkpoint & replay | Event-sourced state |
| Actor identity | Execution name | Entity key |
| Concurrency model | Single-threaded per execution | Single-threaded per entity |
| Billing model | Per execution time | Per execution time |

AWS durable functions emphasize workflow-oriented durability, while Azure
Durable Entities expose a more explicit actor API.

---

### 5.2 Comparison with Classical Actor Frameworks

| Property | Akka / Orleans | Durable Functions |
|--------|----------------|------------------|
| Compute model | Long-lived processes | Ephemeral executions |
| State | In-memory / persisted | Persisted checkpoints |
| Activation | Explicit / implicit | Implicit |
| Scaling | Actor placement | Serverless scaling |
| Cost model | Provisioned resources | Pay-per-execution |

Durable functions trade fine-grained control for elasticity and cost efficiency.

---

## 6. Fault Tolerance and Guarantees

Durable execution relies on **checkpoint-and-replay**:
- completed steps are persisted,
- failures cause re-execution from the last checkpoint,
- side effects must be isolated to steps.

This approach provides:
- at-least-once execution at the step level,
- effectively exactly-once state transitions for deterministic steps.

This is conceptually similar to:
- event sourcing in actor systems,
- distributed logs in stream processing systems.

---

## 7. Implications for Serverless System Design

Durable functions enable new classes of serverless applications:

- long-running workflows without idle compute cost,
- stateful coordination without external databases,
- actor-like systems without managing actor lifecycles.

Patterns that become practical:
- supervisors and worker hierarchies,
- stateful pipelines,
- fault-tolerant orchestration at scale.

However, limitations remain:
- restricted execution models,
- reliance on deterministic code,
- limited control over scheduling and placement.

---

## 8. Summary

This phase demonstrates that AWS Lambda Durable Functions implement a
**serverless-compatible variant of the actor model**.

They satisfy core actor properties while adapting them to the constraints of
serverless computing, particularly cost efficiency and elasticity.

Durable functions should be viewed not as a replacement for classical actor
frameworks, but as a complementary abstraction for stateful, elastic workflows
in cloud-native systems.
