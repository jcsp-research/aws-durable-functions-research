# Phase 3: Actor Model Analysis

**Objective:** Position AWS Lambda Durable Functions within the broader actor model
landscape and evaluate their conceptual alignment with established actor systems.

**Reference:** Spenger, J., Carbone, P., and Haller, P. (2024). A Survey of Actor-Like
Programming Models for Serverless Computing. LNCS 14360, pp. 123–146. Springer.
https://doi.org/10.1007/978-3-031-51060-1_5

---

## 1. Actor Model Alignment

The canonical actor model (Hewitt, Bishop & Steiger, 1973) defines three properties:
- **Full state encapsulation** — private state, no shared memory
- **Location transparency** — addressed by identity, not location
- **Sequential processing** — messages processed one at a time

| Property | AWS Lambda DF | Evidence |
|---|---|---|
| Unique identity | ✓ | `execution_name` as persistent idempotency key |
| Sequential processing | ✓ | Steps execute one at a time; verified in 16-event history (Phase 1) |
| Fault tolerance | ✓ | Transparent retry with exponential backoff (10→87s); checkpoint-and-replay |
| Actor-to-actor messaging | ✗ | No messaging between durable executions |
| Dynamic actor creation | ✗ | An execution cannot spawn sub-executions as child actors |
| Persistent entity | ✗ | Workflow has bounded lifecycle; no EntityId across invocations |

**Taxonomy (Spenger et al.):** AWS Lambda DF classify as *reliable actor orchestration*
— full coverage of state management, fault tolerance, and ordering; no messaging or
dynamic composition.

---

## 2. Comparison with Related Systems

| System | State | Messaging | Fault tolerance | Latency | Deployment |
|---|---|---|---|---|---|
| Akka (JVM) | In-memory | ✓ Native async | Supervision hier. | μs | Dedicated server |
| Orleans (MS) | Virtual + pluggable | ✓ At-most-once | Silo reactivation | ms (warm) | Cloud clusters |
| Azure Durable Entities | Durable (Storage) | ✓ Signaling | At-least-once | 100–500 ms | Serverless (Azure) |
| Temporal | Durable (log) | △ Ext. signals | At-least-once | 100–300 ms | Server / SaaS |
| Cloudburst | Cache (Anna KVS) | ✓ Causality | Cache-level | <1 ms | Research (Lambda) |
| Crucial (URV) | Distributed obj. | △ Indirect | Store-level | 10–50 ms | Research (Lambda) |
| **AWS Lambda DF** | Checkpoint SDK | ✗ Absent | Retry + replay | 630–9300 ms | Serverless native |

### Key comparisons

**vs Azure Durable Entities:** Azure goes significantly further — each entity has a
persistent `EntityId` across calls and operations can be signaled between entities.
AWS DF model a bounded-lifecycle workflow, not a persistent entity.

**vs Orleans:** Orleans holds grain state in silo memory (μs–ms latency, thousands
of ops/s). AWS DF persist to external storage on every checkpoint (~150–200 ms per
step), eliminating silo management at the cost of higher per-step latency.

**vs Cloudburst/Crucial (URV):** Both are academic systems built on top of Lambda.
Cloudburst achieves sub-millisecond latency via Anna KVS cache. AWS DF is the only
tier-1 provider native implementation, making it production-ready without additional
infrastructure.

---

## 3. Fault Tolerance and Execution Guarantees

- **Execution semantics:** at-least-once (a Lambda invocation may be retried)
- **Step result semantics:** effectively-exactly-once (a completed step's result
  is checkpointed and never re-executed, even across retries)
- **External effects:** at-least-once — the SDK cannot guarantee idempotency of
  API calls or database writes; this is the programmer's responsibility

**Relation to event sourcing:** The checkpoint store functions as an append-only
event log — each `StepSucceeded` event is immutable. This is architecturally
equivalent to event sourcing but scoped to a single workflow execution rather than
an aggregate's full lifetime.

---

## 4. New Patterns Enabled

1. **AI agent pipelines** — each LLM tool call is a checkpointed step; transient
   failures do not re-invoke the LLM
2. **Recoverable ETL workflows** — idempotency by design, no manual token management
3. **Human-in-the-loop flows** — `context.wait_for_event()` suspends execution
   without billing until an external callback arrives
4. **Microservice sagas** — compensating transactions without a separate saga state
   store or orchestrator database

---

## 5. Limitations and Open Questions

1. **No parallelism (SDK v12–v13):** `context.parallel()` and `context.map()` are
   non-functional in Python (`SerDesError: Unsupported type: <class 'function'>`).
   This is the most critical missing feature relative to ExCamera/Sprocket.

2. **Fragmented observability:** A durable execution spans multiple Lambda invocations
   with separate CloudWatch log streams; no single metric covers total execution cost.

3. **No actor-to-actor messaging:** Coordination across executions must be implemented
   externally (e.g., via SQS or EventBridge), negating part of the serverless simplicity.

4. **SDK maturity:** Evaluated at v12–v13 (April 2026). Many limitations may be
   resolved as the SDK matures.
