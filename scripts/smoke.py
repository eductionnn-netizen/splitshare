"""Run and verify the built artifact, not the source module."""
import json
from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parents[1]
result = subprocess.run([sys.executable, str(root / "dist/splitshare.pyz"),
                         str(root / "examples/weekend.json")],
                        check=True, capture_output=True, text=True)
data = json.loads(result.stdout)
expected = {"Аня": 170000, "Борис": -40000, "Вика": -130000}
if data["balances_kopecks"] != expected:
    raise SystemExit("Smoke failed: incorrect balances")
if sum(t["amount_kopecks"] for t in data["transfers"]) != 170000:
    raise SystemExit("Smoke failed: incorrect transfers")
print(result.stdout)
report = subprocess.run([sys.executable, str(root / "dist/splitshare.pyz"),
                         str(root / "examples/weekend.json"), "--format", "text"],
                        check=True, capture_output=True, text=True)
if "Вика → Аня: 1300.00 ₽" not in report.stdout or "Борис → Аня: 400.00 ₽" not in report.stdout:
    raise SystemExit("Smoke failed: incorrect text report")
print(report.stdout)
print("SMOKE PASSED: built SplitShare artifact executed successfully")
