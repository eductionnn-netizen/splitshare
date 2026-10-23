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

# Exercise the packaged web app with an isolated database and an ephemeral port.
import select
import tempfile
from urllib.request import Request, urlopen

with tempfile.TemporaryDirectory() as folder:
    process = subprocess.Popen([sys.executable, str(root / "dist/splitshare-web.pyz"),
                                "--port", "0", "--database", str(Path(folder) / "smoke.sqlite3")],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        ready, _, _ = select.select([process.stdout], [], [], 10)
        if not ready:
            raise SystemExit("Web smoke failed: server startup timed out")
        line = process.stdout.readline().strip()
        if not line.startswith("SplitShare: http://127.0.0.1:"):
            raise SystemExit("Web smoke failed: " + line)
        base = line.removeprefix("SplitShare: ")
        with urlopen(base, timeout=5) as page:
            if b"expense-form" not in page.read():
                raise SystemExit("Web smoke failed: missing interface")
        for asset in ("/app.js", "/style.css"):
            with urlopen(base + asset, timeout=5) as resource:
                if not resource.read():
                    raise SystemExit("Web smoke failed: empty asset")
        def post(path, payload):
            request = Request(base + path, data=json.dumps(payload).encode(),
                              headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read())
        group = post("/api/groups", {"name": "Smoke", "members": ["Anna", "Boris"]})
        result = post("/api/groups/" + group["id"] + "/expenses", {
            "id": "smoke", "title": "Dinner", "date": "2026-10-23", "payer": "Anna",
            "amount_kopecks": 101, "participants": ["Anna", "Boris"]})
        if result["result"]["balances_kopecks"] != {"Anna": 50, "Boris": -50}:
            raise SystemExit("Web smoke failed: incorrect calculation")
        print("WEB SMOKE PASSED: packaged UI, API and SQLite persistence")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
