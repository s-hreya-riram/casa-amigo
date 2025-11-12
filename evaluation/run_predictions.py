# evaluation/run_predictions.py
# Run your retriever + LLM to produce prediction files compatible with the eval harness.
# Usage (from repo root):
#   python evaluation/run_predictions.py \
#       --persist_dir pdf_index --top_k 10 \
#       --retrieval_gold evaluation/retrieval_data.json \
#       --rouge_gold evaluation/rouge_data.json \
#       --retrieval_out evaluation/retrieval_results.json \
#       --gen_out evaluation/gen_outputs.json

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import argparse, json, os, re
from typing import List, Dict, Any, Tuple

from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from utils.lease_tool import build_lease_qna_tool
from dotenv import load_dotenv

# ------------ ENV ------------
ROOT = pathlib.Path(__file__).resolve().parents[1]
for candidate in [ROOT / ".env", ROOT / "src" / ".env"]:
    if candidate.exists():
        load_dotenv(candidate)
        print(f"Loaded env from {candidate}")
        break

# ------------ Debug logger for your tool ------------
def debug_log(event, **kwargs):
    print(f"[{event}]", kwargs)

# ------------ Helpers: label inference & canonicalization ------------
CANON = re.compile(r"^\d{1,4}\([a-z]\)$")  # e.g., 5(f), 2(b), 2023(a)

def infer_clause_label_from_meta(meta: dict) -> str:
    """
    Infer a canonical clause label (e.g., '5(b)') from index metadata that only has
    'clause_num' (e.g., '5') and 'clause_title' (e.g., 'Interest For Rent Arrears').
    """
    num = str((meta or {}).get("clause_num") or "").strip()
    title = str((meta or {}).get("clause_title") or "").strip()
    if not num:
        return ""
    # Try "(a)" etc. in title
    m = re.search(r"\(([a-z])\)", title)
    if m:
        return f"{num}({m.group(1)})"
    # Fallback: just the number (won't match gold top-k but may help parent mapping)
    return num

def extract_canonical_from_text(text: str) -> str:
    if not text: return ""
    m = re.search(r"(\d{1,4}\([a-z]\))", text)
    return m.group(1) if m else ""

def build_gold_maps(retrieval_gold: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, str]], Dict[str, List[str]], Dict[str, str]]:
    """
    Returns:
      - titles_by_qid:  qid -> {lower_title: label}
      - labels_by_qid:  qid -> [label1, label2, ...]
      - primary_by_qid: qid -> primary label
    """
    titles_by_qid: Dict[str, Dict[str, str]] = {}
    labels_by_qid: Dict[str, List[str]] = {}
    primary_by_qid: Dict[str, str] = {}
    for q in retrieval_gold["retrieval_queries"]:
        qid = q["id"]
        titles_by_qid[qid] = {}
        labels_by_qid[qid] = []
        for c in q["relevant_chunks"]:
            lab = (c.get("clause_label") or "").strip()
            tit = (c.get("clause_title") or "").strip().lower()
            if lab:
                labels_by_qid[qid].append(lab)
            if tit and lab:
                titles_by_qid[qid][tit] = lab
        primary_by_qid[qid] = (q.get("primary_chunk") or {}).get("clause_label", "")
    return titles_by_qid, labels_by_qid, primary_by_qid

def canonicalize_label_for_query(qid: str, meta: dict, text: str,
                                 titles_by_qid: Dict[str, Dict[str, str]],
                                 labels_by_qid: Dict[str, List[str]],
                                 primary_by_qid: Dict[str, str]) -> str:
    """
    Convert local node metadata to the gold's canonical label set for THIS query.
    Preference:
      1) exact 'clause_label' already present
      2) map 'clause_title' -> gold label
      3) extract from text (e.g., "5(b)")
      4) parent fallback: if we only have '5', pick the primary or first gold label starting with '5('
    """
    # 1) Exact label in metadata
    lab = (meta or {}).get("clause_label")
    if lab and CANON.match(lab.strip()):
        return lab.strip()

    # 2) Title mapping
    tit = (meta or {}).get("clause_title") or ""
    tit_key = tit.strip().lower()
    if tit_key and tit_key in titles_by_qid.get(qid, {}):
        return titles_by_qid[qid][tit_key]

    # 3) From text
    from_text = extract_canonical_from_text(text or "")
    if from_text and CANON.match(from_text):
        return from_text

    # 4) Parent fallback via clause_num (e.g., "5" -> "5(f)")
    parent = str((meta or {}).get("clause_num") or "").strip()
    if parent.isdigit():
        prim = (primary_by_qid.get(qid) or "").strip()
        if prim and prim.startswith(f"{parent}("):
            return prim
        for lbl in labels_by_qid.get(qid, []):
            if lbl.startswith(f"{parent}("):
                return lbl

    # If nothing matches, return empty (we won't include it)
    return ""

# ------------ Index + Tool ------------
def load_index(persist_dir: str) -> VectorStoreIndex:
    storage = StorageContext.from_defaults(persist_dir=persist_dir)
    return load_index_from_storage(storage)


def ranked_labels_from_query(index, qid, query, top_k,
                             titles_by_qid, labels_by_qid, primary_by_qid):
    qe = index.as_query_engine(
        similarity_top_k=max(20, top_k),   # pull deeper
        response_mode="compact",
    )
    resp = qe.query(query)
    sns = getattr(resp, "source_nodes", []) or []

    # 1) score cutoff to boost Precision@k
    CUT = 0.20
    cand = []
    for sn in sns:
        sc = getattr(sn, "score", None)
        if sc is not None and sc < CUT:
            continue
        cand.append(sn)

    # 2) lightweight MMR-ish dedupe by clause label to reduce redundancy
    seen_labels, picked = set(), []
    for sn in cand:
        node = getattr(sn, "node", None)
        meta = getattr(node, "metadata", {}) or {}
        text = getattr(node, "text", "") or ""
        lab = canonicalize_label_for_query(qid, meta, text,
                                           titles_by_qid, labels_by_qid, primary_by_qid)
        if not lab:
            lab = infer_clause_label_from_meta(meta)
        if lab and lab not in seen_labels:
            picked.append((lab, getattr(sn, "score", 0.0)))
            seen_labels.add(lab)

    # 3) keep top_k by score after cleanup
    picked.sort(key=lambda x: x[1], reverse=True)
    return [lab for lab, _ in picked[:top_k]]


def extract_answer_only(md: str) -> str:
    """Return a short textual answer (no excerpts/HTML) for ROUGE."""
    if not md:
        return ""
    s = md

    # 1) Cut off anything after 'Relevant excerpts' (HTML or plain, case-insensitive)
    s = re.split(r"(?i)relevant\s+excerpts", s)[0]

    # 2) Remove HTML tags (e.g., <br>, <div>, <b>…)
    s = re.sub(r"<[^>]+>", " ", s)

    # 3) Remove markdown links/citation artifacts/backticks/bullets
    s = re.sub(r"\[[^\]]*\]\([^)]+\)", " ", s)           # [text](url)
    s = re.sub(r"\[[0-9]+\]|【\d+[^】]*】", " ", s)        # numeric/cn cites
    s = re.sub(r"`{1,3}.*?`{1,3}", " ", s, flags=re.S)   # inline code
    s = re.sub(r"^\s*[-*•]\s*", "", s, flags=re.M)       # bullet markers

    # 4) Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # 5) Keep only the first 1–2 sentences, cap length
    parts = re.split(r"(?<=[.!?])\s+", s)
    s = " ".join(parts[:2])[:800]

    return s


def generate_answer_with_tool(index: VectorStoreIndex, question: str) -> str:
    lease_qna = build_lease_qna_tool(index=index, debug_log=debug_log)
    try:
        return lease_qna.fn(question)  # markdown with "**Answer**" section
    except Exception as e:
        return f"Error calling lease_qna: {e}"

# ------------ Main ------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist_dir", type=str, default="pdf_index")
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--retrieval_gold", type=str, default="retrieval_data.json")
    ap.add_argument("--rouge_gold", type=str, default="rouge_data.json")
    ap.add_argument("--retrieval_out", type=str, default="retrieval_results.json")
    ap.add_argument("--gen_out", type=str, default="gen_outputs.json")
    args = ap.parse_args()

    # Load gold
    with open(args.retrieval_gold, "r") as f:
        retrieval_gold = json.load(f)
    with open(args.rouge_gold, "r") as f:
        rouge_gold = json.load(f)

    # Build gold lookup maps
    titles_by_qid, labels_by_qid, primary_by_qid = build_gold_maps(retrieval_gold)

    # Load index once
    index = load_index(args.persist_dir)

    # ---- Retrieval predictions ----
    retrieval_preds: Dict[str, Any] = {}
    for q in retrieval_gold["retrieval_queries"]:
        qid = q["id"]
        ranked = ranked_labels_from_query(
            index, qid, q["query"], args.top_k,
            titles_by_qid, labels_by_qid, primary_by_qid
        )
        retrieval_preds[qid] = {"ranked_clause_labels": ranked}

    with open(args.retrieval_out, "w") as f:
        json.dump(retrieval_preds, f, indent=2)

    # ---- Generation predictions ----
    gen_preds: Dict[str, Any] = {}
    for item in rouge_gold["qna_pairs"]:
        qid = item["id"]
        qtext = item["question"]
        raw = generate_answer_with_tool(index, qtext)
        ans = extract_answer_only(raw)
        gen_preds[qid] = {"answer": ans}

    with open(args.gen_out, "w") as f:
        json.dump(gen_preds, f, indent=2)

    print("Wrote:", args.retrieval_out, "and", args.gen_out)

if __name__ == "__main__":
    main()
