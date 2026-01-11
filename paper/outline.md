# Workshop Paper Outline (6 pages)

## 1. Introduction
- Motivation: stateful serverless + AWS durable execution
- Research questions
- Contributions

## 2. Background
- Serverless fundamentals
- Checkpoint-and-replay
- Actor model + virtual actors
- Related systems: Azure Durable Functions, ExCamera

## 3. Durable Functions in AWS Lambda
- SDK primitives: step, wait, parallel/map, callbacks
- Failure/retry semantics
- Guarantees and limitations

## 4. Evaluation
### Phase 1: Counter entity
- latency, replay overhead, ordering, idempotency, state size, cost

### Phase 2: Video encoding pipeline
- parallelism, end-to-end latency, failure recovery, cost
- comparison vs Lambda + DynamoDB/S3

## 5. Discussion: Mapping to Actor Model
- Which actor properties are met / missing
- Patterns enabled and open questions

## 6. Conclusion & Future Work

