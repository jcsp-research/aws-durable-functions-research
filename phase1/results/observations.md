# Phase 1 Observations

## 1. Overview

This document summarizes the main observations obtained from the Phase 1 evaluation of the durable counter workflow implemented with AWS Lambda Durable Functions.

The experiments were organized into three groups:

1. **Normal execution**
2. **Controlled failure**
3. **Concurrency**

Across all successful executions, the workflow preserved the same ordered structure:

- `initialize_counter`
- `apply_counter_operation`
- `build_response`

---

## 2. Normal Execution

### 2.1 Objective

The purpose of the normal execution experiments was to verify:

- deterministic step ordering,
- correctness of state transitions,
- consistency of version updates,
- correct read-only behavior for state retrieval.

### 2.2 Observed behavior

| Event | Initial State | Operation | Final State | Status | Duration (s) |
|---|---|---|---|---|---:|
| `event_increment_2.json` | `value = 0`, `version = 0` | `increment(2)` | `value = 2`, `version = 1` | Succeeded | 4.240 |
| `event_decrement_1.json` | `value = 2`, `version = 1` | `decrement(1)` | `value = 1`, `version = 2` | Succeeded | 4.271 |
| `event_get_value.json` | `value = 1`, `version = 2` | `get_value` | `value = 1`, `version = 2` | Succeeded | 0.866 |

### 2.3 Observations

- All normal-execution experiments completed successfully.
- The workflow preserved deterministic step ordering across all successful runs.
- State transitions were correct for both increment and decrement operations.
- The `version` field increased consistently when the state was mutated.
- The `get_value` operation returned the stored state without modifying it.
- No retries or failures were observed during normal execution.

### 2.4 Interpretation

These results indicate that the workflow behaves deterministically under nominal conditions and preserves consistent state evolution across successive invocations. The read-only operation further confirms that the workflow can retrieve persisted state without introducing unintended modifications.

---

## 3. Controlled Failure

### 3.1 Objective

The controlled-failure experiments were designed to evaluate:

- retry behavior,
- backoff between retries,
- step-level atomicity,
- whether state changes inside a failed step are committed.

### 3.2 Observed behavior

| Event | Failure Mode | Status | Retries Observed | Final Outcome | Duration (s) |
|---|---|---|---:|---|---:|
| `event_fail_once_increment.json` | `once` | Failed | Not reliably measured | The step failed and the transient-failure marker was not preserved across retries | -- |
| `event_fail_increment.json` | `always` | Failed | 5 | The workflow terminated in failure after repeated retries | 205.386 |

### 3.3 Observations

- In both failure experiments, `initialize_counter` completed successfully.
- In both failure experiments, `apply_counter_operation` failed.
- In neither case did the workflow reach `build_response`.
- The permanent-failure experiment showed repeated retries of the same failing step.
- The delay between retries increased progressively, indicating backoff behavior.
- In the failed-once experiment, the transient-failure marker introduced inside the failing step did not survive across retries.

### 3.4 Interpretation

These observations strongly suggest **step-level atomicity**. State mutations introduced inside a failing step do not appear to be committed before retry. The permanent-failure scenario additionally shows that the runtime retries the same failing step multiple times before terminating the execution, with increasing delay between attempts, consistent with a retry-backoff policy.

---

## 4. Concurrency

### 4.1 Objective

The concurrency experiments were intended to evaluate:

- isolation across simultaneous executions,
- absence of shared mutable state,
- consistency of outputs under concurrent invocation,
- latency variation across repeated concurrent runs.

### 4.2 Observed behavior

| Event | Final State | Status | Duration (s) |
|---|---|---|---:|
| `concurrent_inc_1.json` | `value = 1`, `version = 1` | Succeeded | 3.636 |
| `concurrent_inc_2.json` | `value = 1`, `version = 1` | Succeeded | 4.104 |
| `concurrent_inc_3.json` | `value = 1`, `version = 1` | Succeeded | 0.944 |
| `concurrent_inc_4.json` | `value = 1`, `version = 1` | Succeeded | 0.902 |
| `concurrent_inc_5.json` | `value = 1`, `version = 1` | Succeeded | 0.884 |

### 4.3 Observations

- All five concurrent executions completed successfully.
- All five produced the same output: `value = 1`, `version = 1`.
- No evidence of shared mutable state was observed.
- No interference between concurrent executions was visible in the observed results.
- Later concurrent runs exhibited substantially lower latency than the initial ones.

### 4.4 Interpretation

The concurrency experiments indicate strong execution isolation: each invocation appears to evolve independently from its input state rather than updating a globally shared counter. The lower latency observed in later runs is consistent with warm execution environments or container reuse in the underlying serverless platform.

---

## 5. Cross-Experiment Conclusions

The Phase 1 experiments support the following conclusions:

1. **Deterministic execution**  
   Successful runs preserved the same ordered workflow structure and produced expected outputs.

2. **Correct state evolution**  
   Increment and decrement operations updated both the counter value and version consistently.

3. **Read consistency**  
   The read-only operation returned the current state without introducing changes.

4. **Retry and backoff behavior**  
   Controlled failures triggered repeated retries with increasing delay between attempts.

5. **Step-level atomicity**  
   Failed steps did not appear to commit partial state changes before retry or workflow termination.

6. **Concurrency isolation**  
   Concurrent executions behaved as independent workflow instances and showed no evidence of shared-state interference.

7. **Warm execution effects**  
   Later successful executions exhibited lower latency, suggesting execution-environment reuse.

---

## 6. Scope and Limitations

The current Phase 1 experiments provide strong evidence for:

- deterministic workflow execution,
- retry behavior,
- atomicity,
- concurrency isolation.

However, some Phase 1 evaluation aspects remain only partially covered:

- replay-overhead measurement,
- detailed cost comparison against external state storage,
- checkpoint-log size or state-log growth.

These limitations are mainly due to the level of observability exposed by the AWS platform during the current experiments and can be explicitly discussed as future extensions in the paper.
