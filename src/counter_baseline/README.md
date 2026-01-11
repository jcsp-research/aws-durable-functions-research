# Counter (Baseline) – Lambda + DynamoDB

Este módulo implementa el contador usando estado explícito en DynamoDB.

## Requisitos
- Tabla DynamoDB con PK string: `counter_id`
- Variable de entorno:
  - `COUNTER_TABLE` = nombre de la tabla (default: CounterTable)

## Evento directo (invoke)
Increment:

```json
{
  "counter_id": "c1",
  "op": "increment",
  "amount": 3
}

