# AWS Lambda Durable Functions — Empirical Evaluation

[![WOSC 2026](https://img.shields.io/badge/WOSC-2026-blue)](https://workshops.acm.org/serverless)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Artefact repository for the paper:

> **Stateful Serverless in Practice: A First Look at AWS Lambda Durable Functions**  
> Julio César Siguenas Pacheco, Pedro García-López  
> Universitat Rovira i Virgili, Tarragona, Spain  
> *12th International Workshop on Serverless Computing (WOSC '26)*

---

## Repository Structure

    phase1/                          Counter workload — SDK primitives
    ├── code/lambda_function.py      Durable counter (128 MB)
    ├── test-events/                 10 JSON test events
    ├── results/                     9 TXT result logs (re-homologated 2026-04-30)
    ├── cloudwatch/                  Raw CloudWatch CSV exports
    └── report/                      Observations report

    phase2/                          Video encoding — durable vs. traditional
    ├── code/
    │   ├── fase2-lambda_function.py      Durable pipeline (128 MB)
    │   └── fase2-video-traditional.py    Traditional Lambda+DynamoDB (128 MB)
    ├── test-events/                 8 JSON test events
    ├── results/
    │   ├── durable/                 8 TXT — durable approach
    │   └── traditional/             8 TXT — traditional approach
    └── report/                      Evaluation report + cost analysis

    phase3/                          Actor model analysis
    └── phase3-actor-model-analysis.md

---

## Key Findings

> Both functions are configured with **128 MB memory** to ensure an
> isomemory cost comparison.
>
> Phase 1 metrics below correspond to the homologated re-execution
> on **2026-04-30** with runtime `python:3.14.DurableFunction.v13`.
> See `phase1/results/RERUN_NOTES.md` for configuration details.

| Metric | Value |
|--------|-------|
| Checkpoint size (v1 → v101) | 0.025 → 0.029 KB (effectively constant) |
| Cold start overhead | 575–808 ms (n=5) |
| Warm start billed | 445–544 ms |
| Failure backoff (fail_always, 6 attempts) | 2→9→17→27→33 s (non-deterministic) |
| Cost overhead vs traditional (30 s video) | 19.1× |
| Cost overhead vs traditional (60 s video) | 19.3× |
| Cost overhead vs traditional (95 s video) | 16.4× |
| Latency overhead vs traditional | 1.1×–1.5× (converges with load) |
| `context.parallel()` status | ❌ Non-functional — SerDesError (SDK v12–v13) |

---

## Reproducing the Experiments

### Prerequisites

- AWS account with Lambda Durable Functions enabled (us-east-2)
- SDK: `aws_durable_execution_sdk_python`
- Runtime: `python:3.14.DurableFunction.v13`
- DynamoDB table: `durable-failure-markers` (fault injection)
- S3 bucket: `durable-video-artifacts`

### Phase 1 — Counter

Deploy `phase1/code/lambda_function.py` as `fase1-counter-durable` (128 MB,
Python 3.14.DurableFunction runtime), then run each test event:

```bash
aws lambda invoke \
  --function-name fase1-counter-durable \
  --payload file://phase1/test-events/counter_increment_001.json \
  --cli-binary-format raw-in-base64-out \
  response.json
```

Compare output with `phase1/results/counter_increment_001.txt`.

### Phase 2 — Video Pipeline

Deploy both functions with **128 MB memory** for isomemory comparison,
then run test events against each:

```bash
# Durable
aws lambda invoke \
  --function-name phase2-video-durable \
  --payload file://phase2/test-events/video_happy_path_001.json \
  --cli-binary-format raw-in-base64-out response.json

# Traditional
aws lambda invoke \
  --function-name phase2-video-traditional \
  --payload file://phase2/test-events/video_happy_path_001.json \
  --cli-binary-format raw-in-base64-out response.json
```

---

## Citation

```bibtex
@inproceedings{siguenas2026durable,
  title     = {Stateful Serverless in Practice: A First Look at
               {AWS Lambda Durable Functions}},
  author    = {Siguenas Pacheco, Julio C{\'{e}}sar and
               Garc{\'{i}}a-L{\'{o}}pez, Pedro},
  booktitle = {12th International Workshop on Serverless Computing (WOSC '26)},
  year      = {2026},
  publisher = {ACM}
}
```

---

## License

Code: [MIT](LICENSE) · Data and documentation: [CC BY 4.0](LICENSE)
