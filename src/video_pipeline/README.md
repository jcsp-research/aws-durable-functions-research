# Video Encoding Pipeline (Durable Functions) – Phase 2

This module implements a **stateful video encoding pipeline** using **AWS Lambda Durable Functions**.
The goal is to evaluate how durable execution supports **long-running, multi-step workflows**
with parallelism, retries, and failure recovery, compared to traditional serverless approaches.

This implementation is inspired by the **ExCamera** system (Fouladi et al., NSDI 2017), a canonical
serverless workload for distributed video processing.

---

## Motivation

Video encoding is a representative workload for durable functions because it exhibits:

- **Long-running workflows** (minutes rather than milliseconds)
- **Explicit state dependencies** between steps
- **High parallelism** (frame/chunk-level encoding)
- **Failure-prone execution** (spotty I/O, transient errors)
- **Clear cost and performance trade-offs**

This makes it an ideal case study to evaluate **checkpoint-and-replay** semantics in AWS Lambda.

---

## Pipeline Overview

The pipeline consists of the following durable steps:

1. **Validation**
   - Validate input video format and metadata
   - Reject unsupported codecs or resolutions

2. **Chunking**
   - Split the input video into fixed-duration segments (e.g., 1-second chunks)
   - Persist chunk metadata in the durable execution state

3. **Parallel Encoding**
   - Encode each chunk in parallel using `context.map()` / `context.parallel()`
   - Each chunk encoder is executed as an independent durable step
   - Retries are automatically handled by durable execution

4. **Assembly**
   - Collect encoded chunks
   - Reassemble into a final encoded video
   - Ensure correct ordering and codec frame dependencies

Each step is checkpointed, enabling recovery without recomputing completed work.

---

## Durable Execution Semantics

This pipeline relies on the following durable execution primitives:

- `context.step()` for deterministic, checkpointed steps
- `context.map()` / `context.parallel()` for chunk-level parallelism
- Automatic **checkpoint-and-replay** for fault tolerance
- Suspension without compute cost during waits

The durable execution context maintains:
- Current pipeline stage
- Processed chunks
- Encoding parameters
- Intermediate outputs

---

## Failure and Recovery Scenarios

The following failure scenarios are explicitly tested:

- Failure during chunk encoding
- Failure during the assembly step
- Manual termination of the Lambda execution mid-pipeline

In all cases, durable execution is expected to:
- Replay from the last successful checkpoint
- Avoid recomputation of completed steps
- Preserve pipeline correctness

---

## Evaluation Metrics

The following metrics are collected and analyzed:

- **End-to-end latency**
- **Per-chunk encoding time**
- **Parallelism achieved** (number of concurrent chunks)
- **Replay overhead**
- **Checkpoint size growth**
- **Cost per minute of encoded video**

Metrics are extracted from CloudWatch logs and aggregated in notebooks.

---

## Comparison Baseline

A reference implementation using **AWS Lambda + external state storage (DynamoDB / S3)** is provided
in `src/video_baseline/`.

The comparison focuses on:

- Code complexity
- State management effort
- Failure handling logic
- Latency and cost
- Debuggability and observability

---

## Research Questions

This module aims to answer the following questions:

1. How effectively do durable functions support long-running, parallel workflows?
2. What is the overhead of checkpoint-and-replay in realistic pipelines?
3. How does durable execution compare to explicit state management in terms of complexity and cost?
4. To what extent does the pipeline resemble an actor-based system?

---

## Notes

- This implementation prioritizes **clarity and observability** over raw performance.
- Encoding is intentionally simplified (e.g., simulated encoding) to focus on durable execution semantics.
- The design emphasizes deterministic behavior to ensure correct replay semantics.

---

## References

- Fouladi et al., *From Laptop to Lambda: Outsourcing Everyday Jobs to Thousands of Transient Functional Containers*, NSDI 2017 (ExCamera)

