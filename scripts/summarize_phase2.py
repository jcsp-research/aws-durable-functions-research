import pandas as pd

CSV = "experiments/phase2_video_runs.csv"

df = pd.read_csv(CSV, on_bad_lines="skip")

# Convierte a numérico
for col in ["n_chunks", "store_ops", "retries", "time_ms"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Filtra filas válidas
before = len(df)
df = df.dropna(subset=["mode", "n_chunks", "time_ms"])
df = df[df["mode"].isin(["durable-local", "baseline-local"])]
df = df[df["n_chunks"] > 0]          # <-- elimina runs raros n_chunks=0
df = df[df["time_ms"] > 0]
after = len(df)

print("Phase 2 – Video Pipeline Summary")
print(f"Input rows: {before} | Valid rows used: {after}\n")

rows = []
for mode, g in df.groupby("mode"):
    rows.append({
        "mode": mode,
        "runs": len(g),
        "mean_time_ms": round(g.time_ms.mean(), 1),
        "p50_ms": int(g.time_ms.quantile(0.5)),
        "p95_ms": int(g.time_ms.quantile(0.95)),
        "mean_store_ops": round(g.store_ops.mean(), 1),
        "mean_retries": round(g.retries.mean(), 2),
    })

out = pd.DataFrame(rows).sort_values("mode")
print(out.to_string(index=False))

