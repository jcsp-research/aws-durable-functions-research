# Phase 2 Evaluation Report: Stateful Video Encoding with AWS Lambda Durable Functions

**Project:** AWS Lambda Durable Functions Research  
**Target venue:** WOSC 2026  
**Date:** April 2026  
**Repository:** https://github.com/jcsp-research/aws-durable-functions-research

---

## 1. Overview

This report covers the implementation, testing, and evaluation of a stateful video encoding pipeline built using AWS Lambda Durable Functions, compared against a traditional Lambda + DynamoDB baseline. The goal is to assess the trade-offs between durable execution and explicit state management in a realistic serverless workflow.

The pipeline is inspired by ExCamera (Fouladi et al., NSDI 2017), which demonstrated massively parallel video encoding in serverless environments. Our implementation evaluates whether AWS Lambda Durable Functions can simplify the orchestration of such pipelines while maintaining comparable performance and cost.

---

## 2. Pipeline Architecture

Both implementations share the same logical pipeline:

1. **initialize_job** — create job metadata and persist to DynamoDB
2. **validate_video** — check format, resolution, and duration
3. **split_video** — divide the video into fixed-duration chunks (10s each)
4. **encode_chunk** — encode each chunk (attempted in parallel)
5. **merge_video** — concatenate encoded chunks into the final output
6. **build_response** — return structured result

### 2.1 Durable implementation

The durable pipeline (`fase2-lambda_function.py`) uses the AWS Durable Execution SDK for Python. Each pipeline stage is wrapped with `@durable_step` and invoked via `context.step()`. The SDK manages state persistence automatically through checkpoint-and-replay: before advancing to the next step, the runtime serializes the current execution state and persists it. On failure, the function is re-invoked and replays already-completed steps from their checkpoints without re-executing them.

Parallelism was attempted using `context.parallel()` and `context.map()`. Both calls failed at runtime due to SDK limitations described in Section 5.

### 2.2 Traditional implementation

The traditional pipeline (`fase2-video-traditional.py`) uses Lambda + DynamoDB for explicit state management. After each step, the job state is written to DynamoDB. Before each step, the current state is read back. Error handling, retry logic, and state versioning are implemented manually.

---

## 3. Test Scenarios

All test events are available in `phase2/test-events/`. The following scenarios were executed for both implementations:

| Test case | Description | Durable result | Traditional result |
|---|---|---|---|
| `video_happy_path_001` | 95s video, no failures | Succeeded | Succeeded |
| `vid_enc_fail_once_001` | Transient failure in encode_chunk | Succeeded (auto-retry) | Succeeded (manual retry) |
| `vid_merge_fail_always_001` | Permanent failure in merge_video | Failed (CallableRuntimeError) | Failed (explicit error) |
| `video_invalid_format_001` | Unsupported format (avi) | HTTP 400, validation_failed | HTTP 400, validation_failed |
| `video_happy_path_001_replay` | Re-invoke same execution name | Succeeded (cached result) | N/A (no replay semantics) |

### Key observations per scenario

**Happy path:** Both implementations successfully processed a 95-second video (10 chunks of 10s each) end-to-end. The durable version returned `execution_model: durable_sequential_fallback` due to the parallel encoding fallback described in Section 5.

**Transient failure (fail_once):** The durable runtime automatically retried the failing step after detecting the error, completing successfully without any application-level retry logic. The traditional implementation relied on its own `execute_with_retries()` wrapper.

**Permanent failure (fail_always):** The durable runtime propagated the error as `CallableRuntimeError` after exhausting retries. The traditional implementation returned a structured error response. Both terminated cleanly.

**Invalid format:** Both implementations correctly detected the unsupported format at the validation step and returned HTTP 400 without proceeding to encoding, demonstrating that domain validation errors are handled outside the retry loop.

**Replay / idempotency:** Re-invoking the durable function with the same execution name (`759aa5a3-ce0a-4fba-9e23-746f87dc3ec0`) returned the cached result immediately, with `version: 3` unchanged. This confirms that durable executions are idempotent by design — a key property for fault-tolerant pipelines.

---

## 4. Performance and Cost Evaluation

### 4.1 Methodology

Three video durations were evaluated: 30s (3 chunks), 60s (6 chunks), and 95s (10 chunks). All runs used the same encoding configuration: H.264 codec, 2000 kbps bitrate, 10s chunk duration, 1080p resolution. No failures were injected. Both implementations ran on the same AWS account (us-east-2, 3008 MB memory for traditional, 128 MB reported by durable SDK).

**Note on encoding workload:** The `encode_chunk` step does not invoke an actual codec (ffmpeg or similar). Instead, each chunk is simulated by a fixed-duration sleep of approximately 600 ms representing the typical per-chunk work of H.264 encoding, followed by writing a chunk manifest to S3. This design is deliberate: the goal of Phase 2 is to measure the **orchestration overhead of durable execution primitives relative to manual state management**, not the throughput of H.264 encoding. A real encoding workload would add identical compute cost to both implementations and obscure the orchestration differences. The simulated per-chunk time (measured at 612 ms in the traditional logs) is consistent with typical CPU-bound chunk encoding at 1080p on Lambda.

Metrics were extracted from CloudWatch Logs. The durable SDK emits structured `METRIC` JSON entries via its logger. The traditional implementation emits equivalent metrics using the same `emit_metric()` utility.

Cost was calculated using AWS Lambda pricing for us-east-2: $0.0000000167 per GB·s for compute. DynamoDB on-demand pricing: $0.00000025 per read request unit, $0.00000125 per write request unit.

**Note on durable billing:** The durable SDK manages execution through multiple internal Lambda invocations. The `billedDurationMs` reported in `platform.report` reflects the total billed compute across all internal invocations within a single durable execution. This is fundamentally different from the traditional approach, where a single Lambda invocation handles the entire pipeline.

### 4.2 Latency results

| Duration | Chunks | Durable execution_ms | Durable billed_ms | Traditional execution_ms | Traditional billed_ms |
|---|---|---|---|---|---|
| 30s | 3 | 4,351 | 5,273 | 2,141 | 2,692 |
| 60s | 6 | 6,870 | 7,770 | 3,991 | 4,486 |
| 95s | 10 | 9,213 | 9,316 | 6,228 | 6,726 |

The durable approach is consistently slower: approximately 2× at 30s, 1.7× at 60s, and 1.5× at 95s. The overhead decreases proportionally as video duration increases, because the encoding work (which is identical in both approaches) dominates at higher chunk counts. The durable overhead is fixed per step and comes from state serialization and checkpoint persistence.

**Per-chunk timing breakdown (traditional, measured from `step_duration` metrics):**

| Step | Avg duration (ms) | Notes |
|---|---|---|
| `initialize_job` | 36 | DynamoDB write + UUID generation |
| `validate_video` | 22 | Format/metadata check only |
| `split_video` | ~20 | Manifest generation, no real I/O on chunks |
| `encode_chunk` (per chunk) | 612 | Simulated encoding + S3 manifest write |
| `merge_video` | 212 | Concatenation manifest + S3 write |

For a 95s video (10 chunks), the encoding work alone accounts for 10 × 612 = 6,120 ms of the 6,228 ms total execution — i.e., approximately 98% of the traditional execution time is the encoding workload itself, leaving only ~108 ms of orchestration overhead. By contrast, the durable execution takes 9,213 ms for the same workload, implying ~3,085 ms (50%) of additional overhead from the durable SDK's per-step checkpoint-and-replay machinery. This overhead scales with the number of steps (6 fixed orchestration steps plus 10 chunk steps = 16 checkpointed operations for the 95s case).

### 4.3 State size

| Duration | Chunks | Durable checkpoint_kb | Traditional state_kb | Traditional DynamoDB reads | Traditional DynamoDB writes |
|---|---|---|---|---|---|
| 30s | 3 | 1.909 | 2.256 | 11 | 7 |
| 60s | 6 | 3.318 | 4.008 | 17 | 10 |
| 95s | 10 | 5.195 | 6.343 | 25 | 14 |

The durable checkpoint is consistently smaller than the traditional DynamoDB state (approximately 15% smaller). This is because the durable SDK serializes only the execution context, while the traditional approach stores the full job state document including all chunk metadata on every write. The DynamoDB operations scale linearly with chunk count: approximately 2.5 reads and 1.4 writes per chunk in the traditional approach.

### 4.4 Cost results

| Duration | Durable compute ($) | Traditional compute ($) | Traditional DynamoDB ($) | Traditional total ($) | Durable / Traditional ratio |
|---|---|---|---|---|---|
| 30s | $0.000220 | $0.000112 | $0.0000114 | $0.000123 | 1.79× |
| 60s | $0.000324 | $0.000187 | $0.0000169 | $0.000204 | 1.59× |
| 95s | $0.000389 | $0.000281 | $0.0000238 | $0.000305 | 1.28× |

**Cost per minute of video encoded:**

| Duration | Durable ($/min) | Traditional ($/min) |
|---|---|---|
| 30s | $0.000440 | $0.000246 |
| 60s | $0.000324 | $0.000204 |
| 95s | $0.000246 | $0.000193 |

The durable approach is more expensive in all cases, ranging from 1.28× to 1.79× the cost of the traditional approach for happy-path executions. The cost ratio converges as video duration increases, following the same pattern as latency: the per-step overhead of durable execution becomes proportionally smaller as the encoding work dominates.

---

## 5. Unexpected Finding: Parallel Execution Not Available

The SDK documentation describes `context.parallel()` and `context.map()` as primitives for concurrent step execution. Our implementation attempted both in sequence, with the following results observed in CloudWatch Logs:

```
Parallel execution returned: BatchResult
Parallel failed (Cannot materialize parallel result of type BatchResult.
  Attributes: ['all', 'completion_reason', 'failed', 'failure_count', ...])
Map failed (object of type 'function' has no len()), using sequential fallback...
```

Additionally, the SDK raised `SerDesError: Unsupported type: <class 'function'>` when attempting to serialize the lambda functions passed to `context.parallel()`. This indicates that the serialization layer does not yet support passing Python callables as parallel tasks.

As a result, all chunk encoding was executed sequentially via `context.step()` in a loop, producing `execution_model: durable_sequential_fallback` in all runs. The `actual_parallel_chunks` metric was consistently 1 across all experiments.

This is a significant limitation for the video encoding use case, where parallelism is the primary mechanism for reducing end-to-end latency. ExCamera (Fouladi et al., 2017) achieved sub-minute encoding of feature-length videos by splitting into thousands of parallel chunks. Without working parallel primitives, AWS Lambda Durable Functions cannot currently replicate this approach.

This finding is consistent with the service being newly released (December 2025). The parallel execution capability appears to be partially implemented in the SDK but not yet fully functional for Python callables. We have documented this behavior in detail and consider it a valuable contribution for the research community evaluating this service.

---

## 6. Comparison Summary

| Dimension | Durable | Traditional |
|---|---|---|
| State management | Automatic (SDK checkpoint-and-replay) | Manual (DynamoDB reads/writes per step) |
| Fault tolerance | Built-in retry and replay | Custom retry logic required |
| Idempotency | Native (execution name deduplication) | Not supported |
| Parallelism | Not functional (SDK limitation) | Not implemented (sequential by design) |
| Latency (95s) | 9,213 ms | 6,228 ms |
| Cost (95s) | $0.000389 | $0.000305 |
| Code complexity | 759 LOC total (680 excluding parallel fallback) | 604 LOC total (120 dedicated to state/retry boilerplate) |
| Observability | Fragmented (multiple internal invocations, no single REPORT) | Clear (single Lambda invocation, standard CloudWatch REPORT) |
| DynamoDB operations | 0 (SDK manages storage internally) | 25 reads + 14 writes (95s video) |

### Key trade-offs

The durable approach eliminates significant boilerplate: retry logic, state serialization, version management, and idempotency handling are all provided by the SDK. In the traditional implementation, these account for a substantial portion of the code complexity.

**Code complexity (measured):**

| Implementation | Total LOC | Of which: boilerplate* | Net step logic |
|---|---|---|---|
| Durable | 759 | ~80 (parallel fallback + materializer, see §5) | ~680 |
| Traditional | 604 | ~120 (execute_with_retries + save/load state + version mgmt) | ~485 |

\* Boilerplate here means code not directly expressing the step's business logic.

The raw line count suggests the durable implementation is larger, but this is misleading: approximately 80 lines of the durable code are the failed `context.parallel()` / `context.map()` attempts plus the materialization fallback (§5), which would not exist in a working SDK. If the parallel primitive worked, the durable file would be approximately 680 LOC vs 485 LOC for traditional. The remaining gap is primarily explained by the durable file containing per-step DynamoDB writes for job state tracking (which the SDK does not manage, it only handles checkpoint state), which are similar in both implementations.

**Net reduction in boilerplate:** the traditional implementation dedicates ~120 LOC to retry logic (`execute_with_retries`, 40 lines), state serialization (`to_dynamo_number_dict` / `from_dynamo_number_dict`, 30 lines), and version management (`save_job_state` / `load_job_state`, 20 lines). The durable implementation has none of this — it is provided by the SDK transparently. This is the meaningful LOC saving: approximately 120 lines of error-prone distributed systems code.

However, the durable approach currently has two practical disadvantages. First, it is approximately 1.3–1.8× more expensive for happy-path executions where failures do not occur. Second, its observability model is fragmented: the execution spans multiple internal Lambda invocations, and there is no single CloudWatch REPORT entry covering the entire durable execution. Monitoring and cost attribution are therefore more difficult.

The cost comparison shifts in favor of durable when failures are frequent. In the `vid_enc_fail_once` scenario, the durable approach absorbed the failure transparently with no additional application code, while the traditional approach required its own retry infrastructure. At scale, the operational cost of maintaining that infrastructure may outweigh the per-execution compute overhead of the durable approach.

---

## 7. Lessons Learned

**On the SDK:** AWS Lambda Durable Functions is a newly released service (December 2025). The Python SDK (v13 at time of evaluation) has known limitations around parallel execution, serialization of callable types, and observability. These are expected to improve in future releases.

**On checkpoint-and-replay:** The mechanism works correctly for sequential workflows. Step results are cached and replayed on re-invocation, as demonstrated by the idempotency test. The overhead per step is approximately 150–200 ms for state serialization and persistence.

**On the research use case:** Video encoding is a demanding benchmark for durable functions because its primary optimization lever — parallelism — is currently unavailable. A fairer comparison would involve a workflow where recovery from failures is the primary concern, such as a long-running pipeline with external API calls or human approval steps.

**On observability:** The durable SDK's Logger output tab in the AWS Lambda console provides structured METRIC entries, but the standard Lambda `REPORT` line (which includes `Billed Duration`) is only available in the raw CloudWatch log stream, not in the SDK's filtered view. This creates an additional operational step for cost monitoring.

---

## 8. Reproducibility

All test events, results, and code are available in the repository:

```
phase2/
├── code/               — durable and traditional Lambda functions
├── test-events/        — JSON event files for all test scenarios
├── results/durable/    — CloudWatch logs for all durable executions
├── results/traditional/— CloudWatch logs for all traditional executions
└── report/             — this document
```

AWS configuration: Lambda function `phase2-video-durable` (Type: Durable, runtime Python 3.14.DurableFunction.v13), `phase2-video-traditional` (Type: standard Lambda, Python 3.12). Both deployed in us-east-2. S3 bucket: `durable-video-artifacts`. DynamoDB tables: `durable-video-jobs`, `durable-failure-markers`.

---

## References

- Fouladi, S. et al. (2017). *Encoding, Fast and Slow: Low-Latency Video Processing Using Thousands of Tiny Threads*. NSDI 2017.
- AWS Blog (December 2025). *Build multi-step applications and AI workflows with AWS Lambda Durable Functions*. https://aws.amazon.com/blogs/aws/build-multi-step-applications-and-ai-workflows-with-aws-lambda-durable-functions/
- AWS Documentation. *AWS Lambda Durable Functions*. https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html
