# Video Encoding Pipeline (Baseline) – Lambda + External State

This module implements a **reference video encoding pipeline** using
**AWS Lambda with explicit external state management** (DynamoDB and/or S3).

It serves as a **baseline** to compare against the durable execution
implementation in `src/video_pipeline/`.

---

## Motivation

Traditional serverless platforms require developers to manage state explicitly.
This baseline implementation represents the **conventional approach** to building
long-running workflows in AWS Lambda prior to the introduction of durable functions.

The purpose of this module is to quantify the **engineering and operational cost**
of explicit state management.

---

## Pipeline Overview

The baseline pipeline follows the same logical stages as the durable version:

1. **Validation**
   - Validate input video format and metadata
   - Persist validation status in external storage

2. **Chunking**
   - Split the input video into fixed-duration segments
   - Store chunk metadata in DynamoDB or S3

3. **Parallel Encoding**
   - Launch independent Lambda invocations per chunk
   - Each encoder:
     - Reads chunk metadata from storage
     - Writes encoded output back to storage
     - Updates processing status explicitly

4. **Assembly**
   - Poll or coordinate via external state
   - Detect when all chunks are ready
   - Assemble the final encoded video

Unlike the durable version, **each step must explicitly read and write state**.

---

## State Management Strategy

State is managed using external services:

- **DynamoDB**
  - Workflow state (current stage, chunk status)
  - Idempotency and retries
- **Amazon S3**
  - Input video
  - Chunked segments
  - Encoded outputs

The application is responsible for:
- Serializing/deserializing state
- Handling partial failures
- Ensuring idempotency
- Cleaning up inconsistent state

---

## Failure Handling

Failure handling is implemented manually:

- Retries must be explicitly coded
- Partial progress must be tracked in storage
- Failed chunks require custom recovery logic
- Duplicate executions must be detected and handled

This contrasts with durable execution, where retries and replay are handled
by the runtime.

---

## Evaluation Metrics

The following metrics are collected:

- **End-to-end latency**
- **Per-chunk encoding latency**
- **Number of storage operations**
- **External state size**
- **Cost of compute + storage**
- **Code complexity** (lines of code, error-handling paths)

These metrics are compared directly with the durable pipeline.

---

## Comparison Focus

This baseline highlights trade-offs in:

- **Code complexity**
- **Operational burden**
- **Debuggability**
- **Performance**
- **Cost efficiency**

The comparison aims to answer:
> What does durable execution remove from the developer’s burden?

---

## Research Questions

This module supports answering:

1. How much complexity is introduced by explicit state management?
2. What are the cost implications of external state storage?
3. How does failure recovery differ from checkpoint-and-replay?
4. Which approach better supports scalable serverless workflows?

---

## Notes

- This implementation prioritizes correctness and transparency over optimization.
- Encoding is simplified or simulated to focus on orchestration complexity.
- The design intentionally mirrors `video_pipeline/` to ensure fair comparison.

---

## References

- Fouladi et al., *From Laptop to Lambda: Outsourcing Everyday Jobs to Thousands of Transient Functional Containers*, NSDI 2017 (ExCamera)

