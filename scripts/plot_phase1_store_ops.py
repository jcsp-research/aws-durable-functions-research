import pandas as pd
import matplotlib.pyplot as plt

# Cargar datos reales
df = pd.read_csv("docs/metrics/phase1_counter_runs.csv")

# Agrupar por modo
g = df.groupby("mode")["store_ops"].mean()

modes = ["baseline-local", "durable-local"]
values = [g.get(m, 0) for m in modes]

plt.figure(figsize=(4, 3))
plt.bar(modes, values)
plt.ylabel("Mean store operations")
plt.title("Phase 1 – Counter coordination overhead")

plt.tight_layout()
plt.savefig("docs/figures/phase1_store_ops_bar.pdf")
plt.savefig("paper/figures/phase1_store_ops_bar.pdf")
plt.close()

print("Saved phase1_store_ops_bar.pdf to docs/figures and paper/figures")

