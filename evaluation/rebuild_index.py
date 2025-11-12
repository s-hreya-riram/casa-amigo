# evaluation/rebuild_index.py
import os, sys, pathlib, importlib.util
from dotenv import load_dotenv

# ------------ ENV ------------
ROOT = pathlib.Path(__file__).resolve().parents[1]
for candidate in [ROOT / ".env", ROOT / "src" / ".env"]:
    if candidate.exists():
        load_dotenv(candidate)
        print(f"Loaded env from {candidate}")
        break
ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF  = os.environ.get("PDF_PATH", str(ROOT / "data" / "contracts" / "Track_B_Tenancy_Agreement.pdf"))
OUT  = os.environ.get("PERSIST_DIR", str(ROOT / "pdf_index_v2"))

# Load src/core/document_manager.py WITHOUT importing src.core.__init__
dm_path = ROOT / "src" / "core" / "document_manager.py"
spec = importlib.util.spec_from_file_location("dm", dm_path)
dm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dm)

mgr = dm.DocumentIndexManager(pdf_path=PDF, persist_dir=OUT)
mgr.rebuild()
print(f"Rebuilt index at: {OUT}")
