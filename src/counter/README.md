# Counter (Durable) – Phase 1

Este módulo implementa un contador usando AWS Lambda Durable Functions (Durable Execution SDK).

## Evento directo (consola / aws lambda invoke)
Ejemplo: increment

```json
{
  "counter_id": "c1",
  "op": "increment",
  "amount": 3,
  "initial": 0
}

