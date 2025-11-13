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
from llama_index.core.postprocessor import SentenceTransformerRerank

from utils.lease_tool import build_lease_qna_tool
from dotenv import load_dotenv


# ------------ ENV ------------
ROOT = pathlib.Path(__file__).resolve().parents[1]
for candidate in [ROOT / ".env", ROOT / "src" / ".env"]:
    if candidate.exists():
        load_dotenv(candidate)
        print(f"Loaded env from {candidate}")
        break

from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding

# V3 embeddings: 3072-dim
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")


# ------------ Debug logger for your tool ------------
def debug_log(event, **kwargs):
    print(f"[{event}]", kwargs)

# ------------ Helpers: label inference & canonicalization ------------

import re
from typing import List, Dict, Any

# ------------- Alias expansion for legal phrasing -------------
ALIAS = {
    "rent": ["arrears","due date","rental"],
    "rent due": ["arrears","due date","payable"],
    "security deposit": ["deposit","bond","refundable deposit"],
    "sublet": ["assignment","subletting","part with possession"],
    "pet": ["animal","dog","cat","birds"],
    "alterations": ["unauthorised alterations","drilling","hacking","changes"],
    "repairs": ["minor repairs","maintenance","replacement"],
    "aircon": ["air conditioning","chemical wash","servicing","gas top up"],
    "notice": ["notice period","inspection","viewing"],
    "renew": ["option to renew","renewal"],
    "stamp": ["stamping","stamp duty"],
    "diplomatic": ["transfer overseas","out of singapore","deported","work permit"],
}

def expand_query(q: str) -> str:
    ql = q.lower()
    extra = []
    for k, vals in ALIAS.items():
        if k in ql:
            extra += vals
    return q if not extra else (q + " " + " ".join(sorted(set(extra))))

# ------------- Numeric/keyword boost -----------------
def numeric_tokens(q: str) -> List[str]:
    # catch $200, 200, 10 days, etc.
    toks = []
    for m in re.finditer(r"\$?\b\d+\b", q):
        toks.append(m.group(0).lstrip("$"))
    for kw in ["days","day","month","months","year","years","per annum","%","percent"]:
        if kw in q.lower():
            toks.append(kw)
    return sorted(set(toks))

def contains_any(text: str, needles: List[str]) -> int:
    tl = text.lower()
    score = 0
    for n in needles:
        if n.isdigit():
            # match numbers loosely
            if re.search(rf"\b{re.escape(n)}\b", tl): score += 1
            if re.search(rf"\$\s*{re.escape(n)}\b", tl): score += 1
        else:
            if n in tl: score += 1
    return score

# ------------- Canonicalize clause label -------------
# ------------ Canonicalize clause label (strict version) ------------
LABEL_RE = re.compile(r"^\d{1,4}\([a-z]\)$", re.I)
FIND_RE  = re.compile(r"\b(\d{1,4}\([a-z]\))\b", re.I)

def canonicalize_label_for_query(
    qid: str,
    meta: dict,
    text: str,
    titles_by_qid: Dict[str, Dict[str, str]],
    labels_by_qid: Dict[str, List[str]],
    primary_by_qid: Dict[str, str],
) -> str:
    """
    Map this node (meta+text) to one of the gold labels for THIS qid
    using:
      1) exact clause_label (if already in canonical form)
      2) exact title → label map from gold
      3) fuzzy title/body substring match
      4) parent-number fallback (e.g. '5' -> '5(f)')
    """
    meta = meta or {}
    text = text or ""

    # 1) Exact label already present
    lab = (meta.get("clause_label") or "").strip()
    if lab and CANON.match(lab):
        return lab

    # 2) Exact title mapping (lowercase key)
    tit = (meta.get("clause_title") or "").strip()
    tit_key = tit.lower()
    gold_title_map = titles_by_qid.get(qid, {})
    if tit_key and tit_key in gold_title_map:
        return gold_title_map[tit_key]

    # 3) Fuzzy title/body mapping using normalized strings
    #    - normalise node title+body
    norm_node = _norm(tit + " " + text)
    if norm_node:
        for gold_title_lc, gold_label in gold_title_map.items():
            norm_gold = _norm(gold_title_lc)
            if norm_gold and norm_gold in norm_node:
                return gold_label

    # 4) Parent-number fallback (e.g. we only see "5" but gold has "5(f)")
    parent = (meta.get("clause_num") or "").strip()
    if not parent:
        # try to read bare number from text like "Clause 5" or "5."
        mnum = re.search(r"\b(?:clause\s*)?(\d{1,4})\b", text, flags=re.I)
        parent = mnum.group(1) if mnum else ""

    if parent.isdigit():
        # prefer primary label if it matches parent
        prim = (primary_by_qid.get(qid) or "").strip()
        if prim and prim.startswith(f"{parent}("):
            return prim

        # else, first gold label with that parent prefix
        for lbl in labels_by_qid.get(qid, []):
            if lbl.startswith(f"{parent}("):
                return lbl

    # If nothing matched, we can't confidently map this node.
    return ""


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

# --- custom reranker (add near your imports) ---
from sentence_transformers import CrossEncoder

class SimpleCrossEncoderReranker:
    """Version-agnostic reranker using a sentence-transformers CrossEncoder."""
    def __init__(self, model_name="mixedbread-ai/mxbai-rerank-large-v1", top_n=10, batch_size=16):
        self.model_name = model_name
        self.top_n = top_n
        self.batch_size = batch_size
        self.model = CrossEncoder(model_name, trust_remote_code=True)

    def rerank(self, query, nodes):
        """nodes: list of (node_obj, score_float)"""
        pairs = [(query, getattr(n, "text", getattr(n, "get_text", lambda: "")())) for n, _ in nodes]
        scores = self.model.predict(pairs, batch_size=self.batch_size)
        # Normalize scores 0–1
        min_s, max_s = float(min(scores)), float(max(scores))
        if max_s > min_s:
            scores = [(s - min_s) / (max_s - min_s) for s in scores]
        rescored = [(nodes[i][0], float(scores[i])) for i in range(len(nodes))]

        rescored.sort(key=lambda x: x[1], reverse=True)
        return rescored[: self.top_n]


def ranked_labels_from_query(
    index,
    qid,                         # <— use the query id
    query,
    top_k,
    titles_by_qid,               # <— gold maps
    labels_by_qid,
    primary_by_qid,
    *args, **kwargs
):

    # --- sanitize inputs ---
    # some harnesses pass a dict or extra args; some pass top_k as a string
    if isinstance(query, dict) and "query" in query:
        query = query["query"]
    if query is None:
        query = ""
    try:
        k = int(top_k)
    except (TypeError, ValueError):
        k = 10  # sensible default

    q_exp = expand_query(str(query))
    num_needles = numeric_tokens(str(query))

    # 1) retrieve deeper with embeddings
    qe = index.as_query_engine(
        similarity_top_k=max(15, k),
        response_mode="compact"
    )
    resp = qe.query(q_exp)
    sns = getattr(resp, "source_nodes", []) or []

    # build (node, score) list
    raw = []
    for sn in sns:
        node = getattr(sn, "node", None)
        sc = float(getattr(sn, "score", 0.0) or 0.0)
        if node is not None:
            raw.append((node, sc))

    # 2) rerank with CrossEncoder (version-agnostic)
    reranker = SimpleCrossEncoderReranker(
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_n=max(10, k)
    )
    reranked = reranker.rerank(q_exp, raw)

    # 3) cutoff + de-dupe + numeric boost
    # 3) cutoff + de-dupe + numeric boost (temporarily no cutoff)
    # CUT = 0.05  # disable for debugging
   # 3) de-dupe + numeric boost (disable cutoff while debugging)
    seen, pool = set(), []
    for node, sc in reranked:
        meta = getattr(node, "metadata", {}) or {}
        txt  = getattr(node, "text", "") or ""

        lab = canonicalize_label_for_query(
            qid,
            meta,
            txt,
            titles_by_qid,
            labels_by_qid,
            primary_by_qid,
        )
        if not lab or lab in seen:
            continue

        boost = contains_any(txt, num_needles)
        pool.append((lab, float(sc) + 0.05 * boost, boost))
        seen.add(lab)

    if not pool:
        # small debug bread-crumb so we can see why
        print(f"[debug] {qid} zero after mapping; sample meta_title=",
            (meta.get('clause_title') or ''), "parent_num=", meta.get('clause_num'))

    pool.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [lab for lab, _, _ in pool[:k]]




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
