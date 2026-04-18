
---

### 4. `phase2/results/summary_table.md` (Para paper)

```markdown
| Métrica | Happy Path | Transient Fail | Permanent Fail | Domain Error |
|---------|------------|----------------|----------------|--------------|
| **Durable Latency** | 10.8s | 8.25s | 63s (timeout) | 1.99s |
| **Traditional Latency** | 6.2s | 4.04s | 2.69s | 0.065s |
| **Durable I/O** | 0 | 0 | 0 | 0 |
| **Traditional I/O** | 39 ops | 27 ops | 18 ops | 3 ops |
| **State Versions** | v3 | v3 | N/A | v1 |
| **HTTP Status** | 200 | 200 | 500 | 400 |
| **Retry Logic** | Automático | Automático | 3 attempts | Ninguno |

