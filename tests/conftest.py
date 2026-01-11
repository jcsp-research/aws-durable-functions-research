import sys
from pathlib import Path

# Add ./src to PYTHONPATH so "import counter" works in tests
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
