# Phase 1 Summary Table

## 1. Normal Execution

| Event | Status | Property Evaluated | Final State | Duration (s) |
|---|---|---|---|---:|
| `event_increment_2.json` | Succeeded | Deterministic execution | `value = 2`, `version = 1` | 4.240 |
| `event_decrement_1.json` | Succeeded | Deterministic execution | `value = 1`, `version = 2` | 4.271 |
| `event_get_value.json` | Succeeded | State consistency | `value = 1`, `version = 2` | 0.866 |

### Notes
- All successful runs followed the same ordered workflow:
  - `initialize_counter`
  - `apply_counter_operation`
  - `build_response`
- No retries were observed in normal execution.

---

## 2. Controlled Failure

| Event | Status | Property Evaluated | Retries | Final Outcome | Duration (s) |
|---|---|---|---:|---|---:|
| `event_fail_once_increment.json` | Failed | Atomicity under retry | Not reliably measured | Step failed and state marker was not preserved across retries | -- |
| `event_fail_increment.json` | Failed | Retry, backoff, atomicity | 5 | Workflow terminated in failure after repeated retries | 205.386 |

### Notes
- In both failure scenarios:
  - `initialize_counter` succeeded
  - `apply_counter_operation` failed
  - `build_response` was not executed
- The `always` case showed increasing delay between retries, consistent with backoff.
- The `once` case suggests that changes introduced inside a failing step were not committed before retry.

---

## 3. Concurrency

| Event | Status | Property Evaluated | Final State | Duration (s) |
|---|---|---|---|---:|
| `concurrent_inc_1.json` | Succeeded | Isolation | `value = 1`, `version = 1` | 3.636 |
| `concurrent_inc_2.json` | Succeeded | Isolation | `value = 1`, `version = 1` | 4.104 |
| `concurrent_inc_3.json` | Succeeded | Isolation | `value = 1`, `version = 1` | 0.944 |
| `concurrent_inc_4.json` | Succeeded | Isolation | `value = 1`, `version = 1` | 0.902 |
| `concurrent_inc_5.json` | Succeeded | Isolation | `value = 1`, `version = 1` | 0.884 |

### Notes
- All five concurrent executions completed successfully.
- All returned the same result.
- No evidence of shared mutable state or interference was observed.
- Lower latency in later runs suggests warm execution behavior.

---

## 4. Consolidated Findings

| Finding | Evidence |
|---|---|
| Deterministic execution | Increment, decrement, and read-only runs completed with consistent ordered steps and expected final states |
| State consistency | `event_get_value.json` returned the expected stored state without modification |
| Step-level atomicity | Failed-step mutations were not preserved across retries |
| Retry with backoff | `event_fail_increment.json` showed repeated retries with increasing delay |
| Concurrency isolation | All concurrent runs produced identical outputs without shared-state effects |
| Warm execution effect | Later concurrent runs completed in under 1 second |
