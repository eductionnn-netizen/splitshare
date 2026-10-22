from pathlib import Path
import shutil
import tempfile
import zipapp


root = Path(__file__).resolve().parents[1]
(root / "dist").mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as folder:
    staging = Path(folder)
    shutil.copy2(root / "app/splitshare.py", staging / "splitshare.py")
    zipapp.create_archive(staging, root / "dist" / "splitshare.pyz",
                         interpreter="/usr/bin/env python3", main="splitshare:main")
print("Built dist/splitshare.pyz")
