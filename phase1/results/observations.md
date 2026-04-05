# Phase 1 – Experimental Observations

## 1. Purpose and Scope

This document reports the results of **Phase 1** of the doctoral exploratory study on **AWS Lambda Durable Functions / Durable Execution**, focusing on a simple stateful counter implemented in Python.

The objective of this phase was to validate, through controlled experiments, the following properties:

1. **Functional correctness** of the counter operations.
2. **Recovery behavior** under transient failures.
3. **Terminal behavior** under persistent failures.
4. **Behavior under concurrent independent invocations**.
5. **Robustness of input validation and error reporting**.
6. **Behavior under manual interruption and subsequent re-execution**.
7. **Idempotency of retries within the same execution context**.

A total of **19 experiments** were executed and analyzed.

---

## 2. Implementation Under Test

The evaluated implementation is a durable workflow composed of three steps:

1. `initialize_counter`
2. `apply_counter_operation`
3. `build_response`

The business logic supports the following operations:

- `increment`
- `decrement`
- `get_value`

The implementation also supports two controlled failure modes:

- `fail_mode = "once"`: the step fails only on the first attempt, using DynamoDB as an external failure marker store.
- `fail_mode = "always"`: the step fails in every retry attempt.

The Lambda handler returns a successful response in the following format:

```json
{
  "statusCode": 200,
  "body": {
    "message": "fase1-counter-durable executed successfully",
    "counter_value": <value>,
    "version": <version>
  }
}
```

---

## 3. Experimental Design

### 3.1 Test Categories

The experiments were grouped into five categories.

| Category | Number of Tests | Goal |
|---|---:|---|
| Normal execution | 5 | Validate the correctness of state transitions |
| Transient failures (`fail_once_*`) | 3 | Validate retry and recovery behavior |
| Persistent failures (`fail_always_*`) | 2 | Validate retry exhaustion and terminal failure |
| Concurrent invocations (`concurrent_inc_*`) | 5 | Validate independence and isolation across simultaneous executions |
| Input validation / edge cases | 2 | Validate explicit rejection of invalid requests |
| Manual interruption and recovery | 1 | Validate external interruption semantics and subsequent re-execution behavior |
| Idempotency within the same execution | 1 | Validate that retries do not duplicate logical effects |

### 3.2 Execution Method

All experiments were executed from the **AWS Lambda console**, using test events and the **Durable executions** tab to inspect:

- final execution status,
- step-level event history,
- number of retries,
- relative execution duration,
- success/failure transitions.

### 3.3 Important Methodological Note

The current concurrency experiments use **identical inputs but independent executions**. Therefore, they validate **execution isolation**, not **shared-state concurrency over a single counter entity**. This distinction is important for interpreting the results correctly.

---

## 4. Complete Experimental Results

### Table 1. Full Results Matrix

| Test Case | Input Summary | Expected Result | Observed Result | Retries | Final Status | Interpretation |
|---|---|---|---|---:|---|---|
| `normal_get_001` | `state={value:0,version:0}`, `get_value` | `value=0`, `version=0` | `counter_value=0`, `version=0` | 0 | Succeeded | Correct read-only behavior; no state mutation |
| `normal_inc_001` | `state={0,0}`, `increment`, `amount=1` | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Correct increment and version advancement |
| `normal_inc_005` | `state={0,0}`, `increment`, `amount=5` | `value=5`, `version=1` | `counter_value=5`, `version=1` | 0 | Succeeded | Correct parameterized increment |
| `normal_dec_001` | `state={10,3}`, `decrement`, `amount=1` | `value=9`, `version=4` | `counter_value=9`, `version=4` | 0 | Succeeded | Correct decrement and version advancement |
| `normal_dec_003` | `state={10,3}`, `decrement`, `amount=3` | `value=7`, `version=4` | `counter_value=7`, `version=4` | 0 | Succeeded | Correct parameterized decrement |
| `fail_once_inc_001` | `state={0,0}`, `increment`, `amount=1`, `fail_once` | first attempt fails; retry succeeds with `value=1`, `version=1` | Final response `counter_value=1`, `version=1` after one failed step and successful retry | 1 | Succeeded | Correct transient failure recovery |
| `fail_once_inc_002` | `state={5,2}`, `increment`, `amount=2`, `fail_once` | first attempt fails; retry succeeds with `value=7`, `version=3` | Final response `counter_value=7`, `version=3` after retry | 1 | Succeeded | Correct transient recovery without duplicate increment |
| `fail_once_dec_001` | `state={7,4}`, `decrement`, `amount=2`, `fail_once` | first attempt fails; retry succeeds with `value=5`, `version=5` | Final response `counter_value=5`, `version=5` after retry | 1 | Succeeded | Correct transient recovery without duplicate decrement |
| `fail_always_inc_001` | `state={0,0}`, `increment`, `amount=1`, `fail_always` | repeated failure; no successful completion | Error: `Simulated permanent failure in apply_counter_operation` | ~5 | Failed | Correct terminal behavior under persistent failure |
| `fail_always_dec_001` | `state={10,5}`, `decrement`, `amount=1`, `fail_always` | repeated failure; no successful completion | Error: `Simulated permanent failure in apply_counter_operation` | ~5 | Failed | Same terminal behavior under persistent failure |
| `concurrent_inc_1` | `state={0,0}`, `increment`, `amount=1` | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `concurrent_inc_2` | same as above | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `concurrent_inc_3` | same as above | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `concurrent_inc_4` | same as above | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `concurrent_inc_5` | same as above | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `invalid_operation_001` | `operation=multiply` | explicit validation failure | Error: `Unsupported operation: multiply` | ~5 | Failed | Invalid business operation rejected, but retried unnecessarily |
| `missing_failure_key_001` | `fail_mode=once` without `failure_key` | explicit validation failure | Error: `fail_mode='once' requires 'failure_key' in the event` | ~5 | Failed | Missing required parameter rejected, but retried unnecessarily |
| `manual_termination_recovery_001` | `state={0,0}`, `increment`, `amount=5`, `debug_sleep_seconds=15` | stopped execution during `apply_counter_operation`; no final state committed; re-execution should succeed from scratch | First execution manually stopped with `initialize_counter` completed and `apply_counter_operation` left in `Started`; second execution succeeded with `counter_value=5`, `version=1` | 0 (stopped execution) / 0 (second execution) | Stopped / Succeeded | Manual interruption does not resume; workflow must be re-executed from the beginning, with no partial visible state |
| `idempotency_same_execution_001` | `state={0,0}`, `increment`, `amount=3`, `fail_once`, `failure_key=phase1-idempotency-test-001` | first attempt fails; retry succeeds with `value=3`, `version=1` and no duplicated increment | Final response `counter_value=3`, `version=1` after one failed step and successful retry | 1 | Succeeded | Correct idempotent retry; logical effect applied exactly once |

---

## 5. Detailed Analysis by Category

### 5.1 Normal Execution

#### Summary

All five normal-operation tests completed successfully and produced the expected outputs.

### Table 2. Normal Execution Results

| Test | Initial State | Operation | Expected Output | Observed Output | Status |
|---|---|---|---|---|---|
| `normal_get_001` | `value=0, version=0` | `get_value` | `value=0, version=0` | `value=0, version=0` | ✅ |
| `normal_inc_001` | `value=0, version=0` | `increment 1` | `value=1, version=1` | `value=1, version=1` | ✅ |
| `normal_inc_005` | `value=0, version=0` | `increment 5` | `value=5, version=1` | `value=5, version=1` | ✅ |
| `normal_dec_001` | `value=10, version=3` | `decrement 1` | `value=9, version=4` | `value=9, version=4` | ✅ |
| `normal_dec_003` | `value=10, version=3` | `decrement 3` | `value=7, version=4` | `value=7, version=4` | ✅ |

#### Findings

1. The workflow is **functionally correct** for all supported operations.
2. The `version` field behaves consistently:
   - it **does not change** for `get_value`,
   - it **increments by one** for each successful state mutation.
3. The step structure was stable in all successful executions:
   - `initialize_counter`
   - `apply_counter_operation`
   - `build_response`

#### Interpretation

These tests validate the correctness of the basic state model and show that the durable workflow behaves deterministically in the absence of injected faults.

---

### 5.2 Transient Failures (`fail_once_*`)

#### Summary

All transient failure experiments showed the same general pattern:

1. the first attempt of `apply_counter_operation` failed,
2. the runtime retried the step,
3. the retry succeeded,
4. the final response remained correct.

### Table 3. Transient Failure Results

| Test | First Attempt | Retry Outcome | Final Output | Status |
|---|---|---|---|---|
| `fail_once_inc_001` | Failed | Succeeded | `value=1, version=1` | ✅ |
| `fail_once_inc_002` | Failed | Succeeded | `value=7, version=3` | ✅ |
| `fail_once_dec_001` | Failed | Succeeded | `value=5, version=5` | ✅ |

#### Findings

1. The retry mechanism is functioning correctly.
2. The DynamoDB failure marker successfully ensures that the failure happens **only once**.
3. No duplicated state updates were observed after retry.

#### Interpretation

These results provide evidence of **retry-safe transient recovery**. Although a step is re-executed, the final effect is logically applied only once. This is one of the most important findings of Phase 1, since it demonstrates controlled fault injection together with consistent recovery behavior.

---

### 5.3 Persistent Failures (`fail_always_*`)

#### Summary

Both persistent failure experiments ended in terminal failure after repeated retries.

### Table 4. Persistent Failure Results

| Test | Error Message | Retry Pattern | Final Status | Interpretation |
|---|---|---|---|---|
| `fail_always_inc_001` | `Simulated permanent failure in apply_counter_operation` | repeated retries, no recovery | Failed | Correct non-recoverable behavior |
| `fail_always_dec_001` | `Simulated permanent failure in apply_counter_operation` | repeated retries, no recovery | Failed | Correct non-recoverable behavior |

#### Findings

1. The runtime attempts to recover from the failure.
2. Because the underlying cause remains unresolved, all retries fail.
3. The workflow does not reach `build_response`.

#### Interpretation

These experiments establish a clear contrast with the `fail_once_*` cases. In Phase 1, this distinction is critical:

- **transient failure** → retried and recovered,
- **persistent failure** → retried and terminated.

This confirms that retries are not sufficient on their own; they only help when the failure condition is temporary.

---

### 5.4 Concurrent Independent Invocations (`concurrent_inc_*`)

#### Summary

All five concurrency experiments used the same payload and all completed successfully with identical outputs.

### Table 5. Concurrent Invocation Results

| Test | Input Type | Output | Status |
|---|---|---|---|
| `concurrent_inc_1` | identical independent request | `value=1, version=1` | ✅ |
| `concurrent_inc_2` | identical independent request | `value=1, version=1` | ✅ |
| `concurrent_inc_3` | identical independent request | `value=1, version=1` | ✅ |
| `concurrent_inc_4` | identical independent request | `value=1, version=1` | ✅ |
| `concurrent_inc_5` | identical independent request | `value=1, version=1` | ✅ |

#### Findings

1. No interference was observed across executions.
2. Each invocation behaved as an isolated workflow.
3. Identical inputs produced identical outputs.

#### Interpretation

These experiments validate **execution isolation** and the absence of implicit shared mutable state across concurrent invocations.

However, this result must be interpreted carefully:

- these tests **do validate** concurrent execution of independent workflows;
- they **do not validate** strict sequential ordering over a single shared durable counter entity.

Therefore, the current Phase 1 concurrency evaluation is valid, but limited in scope. It supports conclusions about isolation, not about actor-style serialized access to shared logical state.

---

### 5.5 Input Validation and Edge Cases

#### Summary

Both edge-case experiments failed explicitly and produced meaningful error messages.

### Table 6. Input Validation Results

| Test | Error Type | Observed Error | Final Status | Interpretation |
|---|---|---|---|---|
| `invalid_operation_001` | unsupported operation | `Unsupported operation: multiply` | Failed | Business input rejected correctly |
| `missing_failure_key_001` | missing mandatory parameter | `fail_mode='once' requires 'failure_key' in the event` | Failed | Invalid request rejected correctly |

#### Findings

1. The implementation rejects invalid requests explicitly.
2. Error messages are clear and useful.
3. The durable runtime still retries these failures several times.

#### Interpretation

Functionally, the validation behavior is correct. Methodologically, however, the retry behavior reveals an inefficiency: deterministic validation errors are treated the same way as transient execution failures.

This suggests a potential improvement area for later phases: introducing explicit classification between:

- retryable failures,
- non-retryable failures.

---



### 5.6 Manual Interruption and Recovery (`manual_termination_recovery_001`)

#### Summary

This experiment was designed to satisfy the Phase 1 requirement of manually interrupting a running durable execution and observing the subsequent behavior.

To make manual interruption feasible from the AWS console, a temporary debug pause (`debug_sleep_seconds=15`) was injected into `apply_counter_operation`. During the first run, the execution was manually stopped while the business step was in progress. The execution status became `Stopped`.

A second run of the same event was then executed without interruption and completed successfully, returning `counter_value=5` and `version=1`.

### Table 7. Manual Interruption and Recovery Result

| Run | Observed Behavior | Final Status | Interpretation |
|---|---|---|---|
| First execution | `initialize_counter` succeeded; `apply_counter_operation` remained started when the execution was manually stopped | Stopped | External interruption prevents completion and no final response is produced |
| Second execution | Full workflow executed successfully and returned `value=5, version=1` | Succeeded | The workflow restarts cleanly from the beginning rather than resuming the stopped execution |

#### Findings

1. Manual interruption is externally observable and leaves the durable execution in `Stopped` state.
2. The interrupted execution does not reach `build_response`.
3. The platform does not resume the stopped execution from the interrupted step.
4. Re-executing the same request produces a clean, correct result.

#### Interpretation

This experiment shows that, in the current Phase 1 design, recovery after manual interruption is **restart-based rather than resume-based**.

No evidence of intermediate state recovery or continuation from the interrupted step was observed. Instead, the interrupted execution remains terminated, and correctness is preserved by launching a new execution from the beginning. This is consistent with the fact that the current Phase 1 workflow keeps state inside the execution context and does not persist partial progress externally.

---

### 5.7 Idempotency within the Same Execution (`idempotency_same_execution_001`)

#### Summary

This experiment validates that retries within the same execution do not produce duplicated state transitions.

A controlled transient failure (`fail_mode="once"`) was injected into `apply_counter_operation` using a dedicated `failure_key`. The first step attempt failed; the runtime retried the same step once; the retry then succeeded.

### Table 8. Idempotency Test Result

| Test | First Attempt | Retry Outcome | Final Output | Retries | Status |
|---|---|---|---|---:|---|
| `idempotency_same_execution_001` | Failed | Succeeded | `value=3, version=1` | 1 | ✅ |

#### Findings

1. The first execution of `apply_counter_operation` failed as expected.
2. The system retried the same step exactly once.
3. The retry succeeded and produced the correct final state.
4. No duplicated increment was observed.

#### Interpretation

This experiment demonstrates that the execution model enforces **idempotent behavior within a single execution context**.

Although the business step was attempted twice due to retry, the final logical state transition was applied only once. This confirms the presence of **exactly-once logical effect under retry**, which is one of the key reliability properties established in Phase 1.

---

## 6. Cross-Cutting Observations

### 6.1 Deterministic Step Structure

Across all successful cases, the workflow followed the same structural pattern:

1. `initialize_counter`
2. `apply_counter_operation`
3. `build_response`

This confirms that the workflow decomposition is stable and that failure injection is localized in the business step.

### 6.2 Retry Semantics

The experiments reveal three retry regimes:

| Scenario Type | Retry Behavior | Outcome |
|---|---|---|
| Normal execution | No retries | Success |
| Transient failures | One failed attempt followed by successful retry | Success |
| Persistent / validation failures | Multiple retries with no recovery | Failure |

This distinction is one of the key empirical outcomes of the phase.

### 6.3 Exactly-Once Logical Effect vs. Multiple Execution Attempts

The `fail_once_*` experiments are particularly important because they show that:

- the system may execute a step more than once,
- but the final logical state update is not duplicated.

This is best described as **exactly-once logical effect under retry**, rather than exactly-once physical execution.

### 6.4 Limitations of the Current Phase 1 Concurrency Design

The current concurrency experiments do not yet satisfy the stronger interpretation of “concurrent updates over a single stateful entity.” They demonstrate isolation, but not ordering over shared state. This should be addressed in later work if the research goal is to assess actor-like sequential processing semantics more directly.

### 6.5 Manual Interruption Semantics

The manual interruption experiment establishes that a stopped execution does not resume automatically. Instead, the workflow must be launched again as a new execution. This means that, in the current Phase 1 setup, resilience under interruption is achieved through **deterministic restart**, not through checkpoint continuation of the interrupted execution.

### 6.6 Idempotency within the Same Execution Context

The idempotency experiment complements the transient-failure experiments by showing that retries do not duplicate logical side effects within a single durable execution. This strengthens the interpretation that Phase 1 provides **exactly-once logical effect under retry**, even though the underlying step may be physically attempted more than once.

---

## 7. Threats to Validity / Limitations

The following limitations should be acknowledged explicitly.

### 7.1 Console-Based Timing Precision

Durations were observed through the Lambda console and durable execution views, not through an automated measurement harness. Therefore, latency interpretation in this phase is approximate.

### 7.2 Concurrency Scope

The concurrency tests validate independent invocations, not conflict resolution over a shared state object.

### 7.3 Error Classification

The current implementation raises generic exceptions for both transient and validation-related issues, which makes it difficult to distinguish operationally between retryable and non-retryable failures.

### 7.4 Temporary Instrumentation for Manual Interruption

The manual interruption experiment required the temporary introduction of an artificial delay (`debug_sleep_seconds`) so that the running execution could be stopped from the AWS console. This instrumentation was used exclusively for experimental observation and should not be interpreted as part of the normal business workflow.

### 7.5 Cost Analysis Not Yet Included

Although Phase 1 called for observing cost-related implications of durable execution, this document does not yet include a quantitative cost comparison. That remains a future enhancement.

---

## 8. Overall Conclusions

Phase 1 can be considered **successfully completed**.

The implementation and experiments jointly demonstrate the following:

1. **Correct functional behavior** of the stateful counter.
2. **Correct durable recovery** from transient step failures.
3. **Expected terminal failure behavior** under persistent faults.
4. **Isolation across concurrent independent executions**.
5. **Explicit rejection of invalid inputs** with informative error messages.
6. **Restart-based behavior after manual interruption**, with no observed continuation of the stopped execution.
7. **Idempotent retry behavior within the same execution context**.

At the same time, the experiments reveal two important limitations:

- the runtime retries deterministic validation failures, which introduces unnecessary overhead;
- the current concurrency tests do not yet demonstrate serialized access to a single shared entity;
- manual interruption recovery in Phase 1 is restart-based, not resume-based.

From a doctoral research perspective, these are not weaknesses of the study; they are useful findings. They help define the next step of the work: moving from isolated durable workflows toward stronger state-sharing and ordering semantics in later phases.

---

## 9. Final Assessment

Phase 1 provides a solid and reproducible empirical foundation for the rest of the thesis work.

Its main contribution is not only that the implementation works, but that it was validated under:

- nominal conditions,
- controlled transient faults,
- controlled persistent faults,
- concurrent independent invocations,
- invalid-input scenarios,
- manual interruption and restart,
- idempotent intra-execution retry scenarios.

This makes the phase suitable as a baseline for:

- the Phase 2 stateful video-processing workflow,
- comparative evaluation against Lambda + external state storage,
- and the later conceptual discussion about actor-like semantics in durable serverless systems.
