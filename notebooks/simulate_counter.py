import pandas as pd, numpy as np, seaborn as sns, matplotlib.pyplot as plt

# Simula 50 ejecuciones
np.random.seed(42)
n = 50
df = pd.DataFrame({
    "execution": [f"durable-{i:02d}" for i in range(1, n+1)],
    "latency_ms": np.random.normal(120, 15, n).round(),
    "replay_ms": np.random.normal(18, 5, n).round(),
    "cost_usd": np.random.normal(0.00010, 0.00001, n).round(6)
})

# Versión "Lambda + DynamoDB" simulada
df_lambda = pd.DataFrame({
    "execution": [f"lambda-db-{i:02d}" for i in range(1, n+1)],
    "latency_ms": np.random.normal(145, 20, n).round(),
    "replay_ms": 0,
    "cost_usd": np.random.normal(0.00018, 0.00002, n).round(6)
})

# Guarda CSV que llenará el notebook
df.to_csv("counter_durable.csv", index=False)
df_lambda.to_csv("counter_lambda_db.csv", index=False)

# Bar-plot rápido
summary = pd.DataFrame({
    "approach": ["Durable", "Lambda+DynamoDB"],
    "avg_latency": [df.latency_ms.mean(), df_lambda.latency_ms.mean()],
    "avg_cost":    [df.cost_usd.mean(),   df_lambda.cost_usd.mean()]
})

sns.barplot(x="approach", y="avg_cost", data=summary)
plt.title("Cost per 50 Invocations (Simulated)")
plt.ylabel("USD")
plt.savefig("../paper/figures/cost_sim.pdf")   # ya lista para incluir
plt.show()
