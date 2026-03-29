# Phase 1 Notes

## General
Phase 1 focused on implementing a durable counter using AWS Lambda Durable Execution and evaluating its execution semantics.

## Key Findings
- Deterministic step ordering was observed in all successful executions.
- Controlled failures triggered repeated retries with increasing delay.
- Failed steps did not partially commit state changes.
- Concurrent executions were isolated and maintained independent execution histories.

## Important Limitation
The current implementation does not model shared mutable state across workflow instances. Each invocation receives its own state as input.

## Next Steps
- Prepare the final LaTeX report
- Add figures from AWS Durable Executions
- Extend the project toward shared-state experiments in Phase 2
