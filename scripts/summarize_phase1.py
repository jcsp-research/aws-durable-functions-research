# scripts/summarize_phase1.py
import pandas as pd

CSV = "experiments/phase1_counter_runs.csv"

REQUIRED = {"run_id", "mode", "final_value", "n_ops", "store_ops", "retries", "time_ms"}

df = pd.read_csv(CSV)

missing = REQUIRED - set(df.columns)
if missing:
    print("Missing columns:", missing)
    print("Got:", list(df.columns))
    exit(1)

# Filtrar ejecuciones inválidas
df = df[df["n_ops"] > 0]

print("\nPhase 1 – Counter Summary")
print("Input rows:", len(df))

summary = (
    df.groupby("mode")
    .agg(
        runs=("run_id", "count"),
        mean_time_ms=("time_ms", "mean"),
        p50_ms=("time_ms", "median"),
        p95_ms=("time_ms", lambda x: x.quantile(0.95)),
        mean_ops=("n_ops", "mean"),
        mean_store_ops=("store_ops", "mean"),
        mean_retries=("retries", "mean"),
        mean_final_value=("final_value", "mean"),
    )
    .round(2)
)

print(summary.to_string())

