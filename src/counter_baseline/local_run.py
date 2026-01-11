from __future__ import annotations

import csv
import os
import time
import uuid

from .store_memory import MemoryCounterStore

# Same command sequence as durable local_run
COMMANDS = [
    ("increment", 1),
    ("increment", 2),
    ("get", 0),
    ("decrement", 1),
]

def _experiments_paths() -> tuple[str, str]:
    here = os.path.dirname(__file__)  # .../src/counter_baseline
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))
    experiments_dir = os.path.join(repo_root, "experiments")
    csv_path = os.path.join(experiments_dir, "phase1_counter_runs.csv")
    return experiments_dir, csv_path

def _ensure_csv(csv_path: str) -> None:
    if os.path.exists(csv_path):
        return
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run_id","mode","final_value","n_ops","store_ops","retries","time_ms"])

def _append_row(csv_path: str, row: list[object]) -> None:
    with open(csv_path, "a", newline="") as f:
        csv.writer(f).writerow(row)

def main() -> None:
    store = MemoryCounterStore(value=0)

    start = time.perf_counter()
    retries = 0  # placeholder for parity with video baseline

    value = store.get()  # initial read (explicit state)

    for op, amount in COMMANDS:
        if op == "increment":
            value = value + int(amount)
            store.put(value)
        elif op == "decrement":
            value = value - int(amount)
            store.put(value)
        elif op == "get":
            value = store.get()
        else:
            raise ValueError(f"Unknown op: {op}")

    elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))

    experiments_dir, csv_path = _experiments_paths()
    os.makedirs(experiments_dir, exist_ok=True)
    _ensure_csv(csv_path)

    run_id = str(uuid.uuid4())[:8]
    n_ops = len(COMMANDS)
    store_ops = int(sum(store.stats.values()))

    _append_row(csv_path, [run_id, "baseline-local", value, n_ops, store_ops, retries, elapsed_ms])

    print("RESULT:", {"value": value, "n_ops": n_ops})
    print("STORE OPS:", store.stats)
    print(f"[experiments] wrote: {csv_path}")

if __name__ == "__main__":
    main()

