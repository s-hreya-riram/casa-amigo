# evaluation/test_index.py
from llama_index.core import StorageContext, load_index_from_storage
import random
import json
import os
import os
from dotenv import load_dotenv
import pathlib

# Load your .env file (works whether it’s in project root or src/)
root_dir = pathlib.Path(__file__).resolve().parents[1]
for candidate in [root_dir / ".env", root_dir / "src" / ".env"]:
    if candidate.exists():
        load_dotenv(candidate)
        print(f"Loaded env from {candidate}")
        break

def main():
    # Path to your persisted index
    persist_dir = os.path.join(os.path.dirname(__file__), "../pdf_index")

    print(f"🔍 Loading index from: {persist_dir}")
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    print("✅ Index loaded successfully!\n")

    # Inspect the first 5 nodes directly
    nodes = list(index.docstore.docs.values())
    print(f"Total chunks in index: {len(nodes)}\n")

    sample_nodes = random.sample(nodes, min(5, len(nodes)))
    for i, n in enumerate(sample_nodes, start=1):
        meta = getattr(n, "metadata", {}) or {}
        print(f"--- Node {i} ---")
        print("Text preview:", (n.text[:160] + "...") if len(n.text) > 160 else n.text)
        print("Metadata keys:", list(meta.keys()))
        for k, v in meta.items():
            print(f"  {k}: {v}")
        print()

    # Run a sample query
    print("\n🧠 Running test query: 'When is rent due?'\n")
    qe = index.as_query_engine(similarity_top_k=5, response_mode="compact")
    resp = qe.query("When is rent due?")
    sns = getattr(resp, "source_nodes", []) or []

    print(f"Top {len(sns)} retrieved chunks:")
    for i, sn in enumerate(sns, start=1):
        meta = getattr(sn.node, "metadata", {}) or {}
        label = meta.get("clause_label") or meta.get("clause_num") or "(no label)"
        title = meta.get("clause_title") or "(no title)"
        print(f"{i}. score={getattr(sn, 'score', None):.3f} | label={label} | title={title}")

        text = (sn.node.text[:140] + "...") if len(sn.node.text) > 140 else sn.node.text
        print(f"   text: {text}\n")

    print("✅ Finished test. Use this output to verify metadata consistency.\n")

if __name__ == "__main__":
    main()
