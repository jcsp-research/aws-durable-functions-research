from __future__ import annotations

import os
import pandas as pd
import matplotlib.pyplot as plt

CSV = "experiments/phase2_video_runs.csv"

OUT_PAPER = "paper/figures/phase2_store_vs_time.pdf"
OUT_DOCS  = "docs/figures/phase2_store_vs_time.pdf"

def main() -> None:
    df = pd.read_csv(CSV)

    # filtra filas inválidas (por si alguna vez aparece n_chunks=0)
    df = df[(df["n_chunks"] > 0) & (df["time_ms"].notna())]

    # scatter store_ops vs time_ms
    plt.figure()
    for mode, g in df.groupby("mode"):
        plt.scatter(g["store_ops"], g["time_ms"], label=mode)

    plt.xlabel("store_ops (explicit state ops)")
    plt.ylabel("time_ms (end-to-end)")
    plt.title("Phase 2: store_ops vs time_ms (local runs)")
    plt.legend()

    os.makedirs("paper/figures", exist_ok=True)
    os.makedirs("docs/figures", exist_ok=True)

    plt.savefig(OUT_PAPER, bbox_inches="tight")
    plt.savefig(OUT_DOCS, bbox_inches="tight")
    print(f"Wrote: {OUT_PAPER}")
    print(f"Wrote: {OUT_DOCS}")

if __name__ == "__main__":
    main()

