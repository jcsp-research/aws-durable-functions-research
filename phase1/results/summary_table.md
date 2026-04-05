# Phase 1 – Final Summary Table

## 1. Overview

This document provides the consolidated summary table for **Phase 1** of the doctoral experimental evaluation of **AWS Lambda Durable Functions / Durable Execution**.

The table synthesizes the complete set of experiments executed in Phase 1 and is intended to complement the detailed analytical narrative presented in `observations.md`.

Phase 1 evaluated the following dimensions:

- functional correctness of a durable counter workflow,
- transient failure handling and retry recovery,
- persistent failure behavior,
- concurrent independent invocation isolation,
- input validation robustness,
- manual interruption and restart behavior,
- idempotency of retries within the same execution.

A total of **19 experiments / observations** are summarized below, including the two-step manual interruption experiment (stopped run + subsequent successful re-execution).

---

## 2. Consolidated Results Matrix

### Table 1. Complete Summary of Phase 1 Experiments

| Test Case | Category | Input Summary | Expected Result | Observed Result | Retries | Final Status | Main Interpretation |
|---|---|---|---|---|---:|---|---|
| `normal_get_001` | Normal execution | `state={0,0}`, `get_value` | `value=0`, `version=0` | `counter_value=0`, `version=0` | 0 | Succeeded | Correct read-only behavior; no mutation |
| `normal_inc_001` | Normal execution | `state={0,0}`, `increment`, `amount=1` | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Correct increment semantics |
| `normal_inc_005` | Normal execution | `state={0,0}`, `increment`, `amount=5` | `value=5`, `version=1` | `counter_value=5`, `version=1` | 0 | Succeeded | Correct parameterized increment |
| `normal_dec_001` | Normal execution | `state={10,3}`, `decrement`, `amount=1` | `value=9`, `version=4` | `counter_value=9`, `version=4` | 0 | Succeeded | Correct decrement semantics |
| `normal_dec_003` | Normal execution | `state={10,3}`, `decrement`, `amount=3` | `value=7`, `version=4` | `counter_value=7`, `version=4` | 0 | Succeeded | Correct parameterized decrement |
| `fail_once_inc_001` | Transient failure | `state={0,0}`, `increment`, `amount=1`, `fail_once` | first attempt fails; retry succeeds with `value=1`, `version=1` | final response `counter_value=1`, `version=1` | 1 | Succeeded | Retry-safe recovery without duplicate increment |
| `fail_once_inc_002` | Transient failure | `state={5,2}`, `increment`, `amount=2`, `fail_once` | first attempt fails; retry succeeds with `value=7`, `version=3` | final response `counter_value=7`, `version=3` | 1 | Succeeded | Correct transient recovery |
| `fail_once_dec_001` | Transient failure | `state={7,4}`, `decrement`, `amount=2`, `fail_once` | first attempt fails; retry succeeds with `value=5`, `version=5` | final response `counter_value=5`, `version=5` | 1 | Succeeded | Correct transient recovery without duplicate decrement |
| `fail_always_inc_001` | Persistent failure | `state={0,0}`, `increment`, `amount=1`, `fail_always` | repeated failures; terminal error | `Simulated permanent failure in apply_counter_operation` | ~5 | Failed | Correct terminal behavior under non-recoverable fault |
| `fail_always_dec_001` | Persistent failure | `state={10,5}`, `decrement`, `amount=1`, `fail_always` | repeated failures; terminal error | `Simulated permanent failure in apply_counter_operation` | ~5 | Failed | Same non-recoverable pattern under decrement |
| `concurrent_inc_1` | Concurrent independent invocation | `state={0,0}`, `increment`, `amount=1` | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `concurrent_inc_2` | Concurrent independent invocation | same as above | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `concurrent_inc_3` | Concurrent independent invocation | same as above | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `concurrent_inc_4` | Concurrent independent invocation | same as above | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Independent execution succeeded |
| `concurrent_inc_5` | Concurrent independent invocation | same as above | `value=1`, `version=1` | `counter_value=1`, `version=1` | 0 | Succeeded | Execution isolation across concurrent runs |
| `invalid_operation_001` | Validation / edge case | `operation=multiply` | explicit validation error | `Unsupported operation: multiply` | ~5 | Failed | Invalid operation rejected, but retried unnecessarily |
| `missing_failure_key_001` | Validation / edge case | `fail_mode=once` without `failure_key` | explicit validation error | `fail_mode='once' requires 'failure_key' in the event` | ~5 | Failed | Missing mandatory parameter rejected, but retried unnecessarily |
| `manual_termination_recovery_001` (run 1) | Manual interruption | `state={0,0}`, `increment`, `amount=5`, `debug_sleep_seconds=15`; manually stopped during `apply_counter_operation` | execution interrupted; no final completion | status `Stopped`; `initialize_counter` completed; `apply_counter_operation` remained started | 0 | Stopped | Manual stop prevents completion and yields no final result |
| `manual_termination_recovery_001` (run 2) | Manual interruption / re-execution | same event, executed without manual stop | full successful completion from scratch with `value=5`, `version=1` | `counter_value=5`, `version=1` | 0 | Succeeded | Recovery is restart-based, not resume-based |
| `idempotency_same_execution_001` | Idempotency within same execution | `state={0,0}`, `increment`, `amount=3`, `fail_once`, `failure_key=phase1-idempotency-test-001` | first attempt fails; retry succeeds with `value=3`, `version=1` and no duplicate effect | final response `counter_value=3`, `version=1`; one failed attempt followed by one successful retry | 1 | Succeeded | Idempotent retry; logical effect applied exactly once |

---

## 3. Metrics-Oriented Synthesis

### Table 2. Behavioral Summary by Experiment Category

| Category | Tests | Typical Retry Pattern | Final Outcome Pattern | Main Property Established |
|---|---:|---|---|---|
| Normal execution | 5 | None | Successful completion | Functional correctness |
| Transient failure (`fail_once_*`) | 3 | One failed attempt, one successful retry | Success after recovery | Retry-safe transient recovery |
| Persistent failure (`fail_always_*`) | 2 | Multiple retries with no recovery | Terminal failure | Non-recoverable fault behavior |
| Concurrent independent invocation | 5 | None | All executions succeed independently | Execution isolation |
| Validation / edge cases | 2 | Multiple retries despite deterministic error | Failure | Explicit validation with retry inefficiency |
| Manual interruption and re-execution | 2 observations | No retry in stopped run; fresh execution afterward | Stopped then succeeded | Restart-based recovery semantics |
| Idempotency within same execution | 1 | One failed attempt, one successful retry | Success without duplicated effect | Exactly-once logical effect under retry |

---

## 4. Key Interpretive Findings

### 4.1 Functional Correctness

The durable workflow correctly implements:

- `get_value`
- `increment`
- `decrement`

with consistent handling of the `version` field:

- unchanged for read-only requests,
- incremented by one for successful state mutations.

### 4.2 Retry Semantics

Phase 1 demonstrates two distinct retry behaviors:

- **recoverable retry** in transient failure scenarios,
- **non-recoverable retry exhaustion** in persistent and validation-driven failure scenarios.

This distinction is central to the reliability analysis of the workflow.

### 4.3 Manual Interruption Semantics

The manual interruption experiment establishes that:

- an externally stopped execution does not resume,
- partial progress is not exposed as a completed final result,
- subsequent recovery requires a **fresh execution**.

Therefore, the current Phase 1 workflow follows a **restart-based recovery model**, not a continuation-based one.

### 4.4 Idempotency

The idempotency experiment confirms that retries within the same durable execution do not duplicate logical effects. Even though the business step is physically attempted more than once, the logical state transition is applied once in the final successful outcome.

This is best characterized as:

> **exactly-once logical effect under retry**

rather than exactly-once physical execution.

### 4.5 Concurrency Scope

The current concurrency tests validate:

- independence,
- isolation,
- absence of implicit shared mutable state across executions.

They do **not** yet validate serialized updates over a single shared counter entity.

---

## 5. Final Assessment

The final summary table confirms that **Phase 1 is experimentally complete** with respect to its intended scope.

The evidence supports the following conclusions:

1. The workflow is functionally correct in normal conditions.
2. Transient faults are handled through successful retry.
3. Persistent faults lead to terminal failure after retry exhaustion.
4. Independent concurrent executions remain isolated.
5. Invalid inputs are rejected explicitly.
6. Manual interruption causes termination, not continuation.
7. Re-execution after interruption is clean and deterministic.
8. Retries inside the same execution do not duplicate logical effects.

Accordingly, Phase 1 provides a solid baseline for later phases focused on stronger state management, richer workflow structures, and more advanced durability semantics.
