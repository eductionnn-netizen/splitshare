from pathlib import Path
import shutil
import tempfile
import zipapp

root = Path(__file__).resolve().parents[1]
(root / "dist").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as folder:
    staging = Path(folder)
    shutil.copy2(root / "app/splitshare.py", staging / "splitshare.py")
    zipapp.create_archive(staging, root / "dist/splitshare.pyz",
                         interpreter="/usr/bin/env python3", main="splitshare:main")
with tempfile.TemporaryDirectory() as folder:
    staging = Path(folder)
    shutil.copytree(root / "app", staging / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    zipapp.create_archive(staging, root / "dist/splitshare-web.pyz",
                         interpreter="/usr/bin/env python3", main="app.web:main")
print("Built dist/splitshare.pyz and dist/splitshare-web.pyz")
