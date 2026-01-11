# ExCamera NSDI 2017 – Quick Notes

- **Fine-grained chunking**: 1-second segments → thousands of parallel Lambda tasks; same strategy we will use in Phase 2.
- **State coordination**: ExCamera used S3 + etcd; Durable Functions replace external state with checkpoint-and-replay, reducing cost and complexity.
