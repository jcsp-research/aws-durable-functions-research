# Phase 1 - Durable Counter

## Objective

Implement and evaluate a durable counter workflow on AWS Lambda Durable Execution.

## Workflow Steps

- `initialize_counter`
- `apply_counter_operation`
- `build_response`

## Supported Operations

- `increment`
- `decrement`
- `get_value`

## Experiments

1. Normal execution
2. Controlled failure
3. Retry and backoff observation
4. Concurrent isolated executions

## Main Findings

- Deterministic workflow execution
- Step-level atomicity
- Automatic retry and backoff
- Strong isolation across concurrent executions
- No shared mutable state across independent executions
