from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class MemoryCounterStore:
    value: int = 0
    stats: Dict[str, int] = field(default_factory=lambda: {"get": 0, "put": 0})

    def get(self) -> int:
        self.stats["get"] += 1
        return self.value

    def put(self, new_value: int) -> None:
        self.stats["put"] += 1
        self.value = int(new_value)

