
### 3. `phase2/results/summary_table.md` (inicial)
```markdown
# Resumen Fase 2 - Video Encoding Pipeline

| Test ID | Tipo | Estado | Duración | Chunks | Versión Final | Observación |
|---------|------|--------|----------|--------|---------------|-------------|
| `video_happy_path_001` | Happy Path | ✅ Succeeded | 10.0s | 10/10 | 3 | Baseline funcional |
| `video_fail_encode_once_005` | Retry | ⏳ Pendiente | - | - | - | Fallo transitorio chunk |
| `video_fail_merge_always` | Límite | ⏳ Pendiente | - | - | - | Fallo permanente |
| `video_large_300s` | Escala | ⏳ Pendiente | - | - | - | 60 chunks (5min video) |
