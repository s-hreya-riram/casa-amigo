# -------------- Clause detection & formatting helpers ------------------
from __future__ import annotations

from typing import Optional, List, Tuple

import re
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex
from llama_index.core.tools import FunctionTool

from utils.utils import (
    detect_clause_label_from_text,
    format_with_citations,
    pretty_lease_output,
    clean_pdf_fragments,
)

from sentence_transformers import CrossEncoder

# ---------------- Query expansion aliases ----------------
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
_RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Global lazy-loaded cross-encoder instance
_reranker_ce: Optional[CrossEncoder] = None


def _get_reranker() -> CrossEncoder:
    """
    Lazily load and cache the CrossEncoder so the model is only created once.
    """
    global _reranker_ce
    if _reranker_ce is None:
        _reranker_ce = CrossEncoder(_RERANK_MODEL_NAME, max_length=512)
    return _reranker_ce


class Reranker:
    """
    Small helper class you can use elsewhere if you need direct scoring.
    This shares the same underlying CrossEncoder as _rerank_source_nodes.
    """

    def __init__(self, model: Optional[CrossEncoder] = None):
        self.model = model or _get_reranker()

    def score(self, query: str, passages: List[str]):
        pairs = [(query, p) for p in passages]
        scores = self.model.predict(pairs)
        # sentence-transformers usually returns a numpy array
        return scores.tolist() if hasattr(scores, "tolist") else scores


def _rerank_source_nodes(query: str, source_nodes, top_n: int = 15):
    """Rerank nodes using CrossEncoder with normalization and numeric boost."""
    if not source_nodes:
        return []

    model = _get_reranker()
    texts = [sn.node.text or "" for sn in source_nodes]
    pairs = [(query, t) for t in texts]
    scores = model.predict(pairs)
    if hasattr(scores, "tolist"):
        scores = scores.tolist()

    # Normalize scores to 0-1
    min_s, max_s = float(min(scores)), float(max(scores))
    if max_s > min_s:
        scores = [(s - min_s) / (max_s - min_s) for s in scores]

    # Apply numeric boost
    nums = _numeric_tokens(query)
    rescored = []
    for i, sn in enumerate(source_nodes):
        txt = texts[i].lower()
        boost = _contains_any(txt, nums)
        rescored.append((sn, scores[i] + 0.05 * boost))

    rescored.sort(key=lambda x: x[1], reverse=True)

    # Deduplicate by clause_label
    seen, final = set(), []
    for sn, sc in rescored:
        meta = getattr(sn.node, "metadata", {}) or {}
        label = meta.get("clause_label") or meta.get("clause_num") or ""
        key = label or id(sn)
        if key in seen:
            continue
        seen.add(key)
        sn.score = sc
        final.append(sn)

    return final[:top_n]



def expand_query(q: str) -> str:
    ql = q.lower()
    extra = []
    for k, vals in ALIAS.items():
        if k in ql:
            extra.extend(vals)
    if not extra:
        return q
    # dedupe extras, keep original first
    extras = " ".join(sorted(set(extra)))
    return f"{q} {extras}"


def _numeric_tokens(q: str) -> List[str]:
    """Catch numbers like 7, 200, 12 and temporal words."""
    toks: List[str] = []
    for m in re.finditer(r"\$?\b\d+\b", q):
        toks.append(m.group(0).lstrip("$"))
    for kw in ["day", "days", "month", "months", "year", "years", "%", "percent"]:
        if kw in q.lower():
            toks.append(kw)
    return sorted(set(toks))


def _contains_any(text: str, needles: List[str]) -> int:
    tl = text.lower()
    score = 0
    for n in needles:
        if n.isdigit():
            if re.search(rf"\b{re.escape(n)}\b", tl):
                score += 1
            if re.search(rf"\$\s*{re.escape(n)}\b", tl):
                score += 1
        else:
            if n in tl:
                score += 1
    return score


def rerank_source_nodes(query: str, sns) -> List:
    """
    Lightweight reranker:
    - keeps nodes as-is (no extra models)
    - boosts based on title overlap + numeric match
    - de-dupes by clause_label
    """
    q = query.lower()
    terms = [t for t in re.findall(r"[a-z]{3,}", q)]
    nums = _numeric_tokens(q)

    scored: List[Tuple[object, float, str]] = []
    seen_labels = set()

    for sn in sns:
        node = getattr(sn, "node", None)
        if node is None:
            continue

        meta = getattr(node, "metadata", {}) or {}
        text = (getattr(node, "text", "") or "").lower()
        title = (meta.get("clause_title") or "").lower()
        label = meta.get("clause_label") or meta.get("clause_num") or ""

        base_score = float(getattr(sn, "score", 0.0) or 0.0)

        # Title term overlap
        title_bonus = sum(1 for t in terms if t in title)

        # Numeric match (e.g. "7 days", "$200")
        num_bonus = _contains_any(text, nums)

        bonus = 0.25 * title_bonus + 0.5 * num_bonus
        scored.append((sn, base_score + bonus, label))

    # sort by combined score
    scored.sort(key=lambda x: x[1], reverse=True)

    # dedupe by clause label, keep order
    reranked = []
    for sn, _, label in scored:
        key = label or id(sn)
        if key in seen_labels:
            continue
        seen_labels.add(key)
        reranked.append(sn)

        return reranked


# -------------- Answer-aware citation helpers ------------------

_WORD_RE = re.compile(r"[A-Za-z0-9$]+")
_CLAUSE_NUM_RE = re.compile(r"^(\d+)", re.I)


def _simple_tokens(text: str):
    text = (text or "").lower()
    return _WORD_RE.findall(text)


def _base_clause_num(meta: dict, text: str = "") -> Optional[str]:
    """Extract the leading clause number like '5' from metadata or inline text."""
    label = (meta or {}).get("clause_label") or (meta or {}).get("clause_num") or ""
    m = _CLAUSE_NUM_RE.match(str(label))
    if m:
        return m.group(1)

    # Fallback: try 'Clause 5(c)' style in the text
    m2 = re.search(r"\bClause\s+(\d+)", text or "", re.I)
    if m2:
        return m2.group(1)

    return None


def _score_node_for_answer(sn, question: str, answer: str) -> float:
    """
    Higher score = better citation candidate.

    We weight overlap with the *answer* more than overlap with the question,
    so we pick the clause that actually supports the wording we used.
    """
    text = getattr(sn.node, "text", "") or ""

    toks_ans = set(_simple_tokens(answer))
    toks_q = set(_simple_tokens(question))
    toks_tx = set(_simple_tokens(text))

    # Overlap with answer is most important
    overlap_ans = len(toks_tx & toks_ans)
    overlap_q = len(toks_tx & toks_q)

    # Small bonus if the clause label appears in the answer text (e.g. "(Clause 5(c))")
    meta = getattr(sn.node, "metadata", {}) or {}
    clause_label = (meta.get("clause_label") or meta.get("clause_num") or "").lower()
    clause_in_answer = 1 if clause_label and clause_label in (answer or "").lower() else 0

    return overlap_ans * 3 + overlap_q + clause_in_answer * 2


def _rank_nodes_for_citation(source_nodes, question: str, answer: str):
    """Return nodes sorted by how well they support the *answer*."""
    scored = []
    for idx, sn in enumerate(source_nodes):
        score = _score_node_for_answer(sn, question, answer)
        scored.append((score, idx, sn))
    # sort by score desc, then by original index to keep behaviour stable
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [sn for _, _, sn in scored]


def _pick_citation_nodes_for_answer(
    source_nodes, question: str, answer: str, max_items: int = 3
):
    """
    Choose which nodes to show as 'Relevant excerpts'.

    Strategy:
    1) Rank nodes by overlap with the *answer* (not just the query).
    2) Always include the top node.
    3) Prefer other nodes that share the same base clause number
       (e.g. 5(c), 5(d), 5(f)).
    4) If we still need more, fill with remaining ranked nodes.
    """
    if not source_nodes:
        return []

    ranked = _rank_nodes_for_citation(source_nodes, question, answer)

    primary = ranked[0]
    chosen = [primary]

    primary_meta = getattr(primary.node, "metadata", {}) or {}
    primary_text = getattr(primary.node, "text", "") or ""
    primary_base = _base_clause_num(primary_meta, primary_text)

    # Prefer siblings like 5(d), 5(f) if primary is 5(c)
    if primary_base:
        for sn in ranked[1:]:
            if len(chosen) >= max_items:
                break
            meta = getattr(sn.node, "metadata", {}) or {}
            text = getattr(sn.node, "text", "") or ""
            base = _base_clause_num(meta, text)
            if base == primary_base:
                chosen.append(sn)

    # If we still don't have enough, just fill from the rest
    for sn in ranked[1:]:
        if len(chosen) >= max_items:
            break
        if sn not in chosen:
            chosen.append(sn)

    return chosen[:max_items]


class LeaseQnAInput(BaseModel):
    input: str


def build_lease_qna_tool(index: VectorStoreIndex, openai_client, llm, debug_log):
    """Return the Lease Q&A FunctionTool using the provided VectorStoreIndex."""
    # retrieve deeper and let our reranker filter down
    qe = index.as_query_engine(
        similarity_top_k=15,          # look a bit deeper
        response_mode="compact",
        llm=llm,
    )

    def lease_qna_fn(input: str) -> str:
        debug_log("tool_called", tool="lease_qna", args={"input": input})
        try:
            expanded = expand_query(input)

            # 1) embedding retrieval
            resp = qe.query(expanded)
            sns = getattr(resp, "source_nodes", []) or []


            # 2) cross-encoder rerank (same behaviour as eval)
            reranked = _rerank_source_nodes(expanded, sns, top_n=15)
            resp.source_nodes = reranked

            # 3) logging top-3 after rerank
            top3 = []
            for i, sn in enumerate(reranked[:3]):
                meta = getattr(sn.node, "metadata", {}) or {}
                label = (
                    (f"Clause {meta.get('clause_label')}: {meta.get('clause_title')}")
                    if meta.get("clause_label") or meta.get("clause_title")
                    else detect_clause_label_from_text(sn.node.text or "")
                ) or (f"Page {meta.get('page_label') or meta.get('page')}")
                top3.append(
                    {
                        "rank": i,
                        "score": getattr(sn, "score", None),
                        "label": label,
                    }
                )

            debug_log("retrieval", tool="lease_qna", retrieved_k=len(reranked), top=top3)

            # 4) low-confidence guard
                      
            

            # 5) pick citation nodes based on the *answer*, then format & prettify
            answer_text = getattr(resp, "response", "") or ""
            # Use reranked list if we have it; otherwise fall back to raw sns
            base_nodes = reranked if reranked else sns
            citation_nodes = _pick_citation_nodes_for_answer(
                base_nodes,
                question=input,
                answer=answer_text,
                max_items=3,
            )
            resp.source_nodes = citation_nodes

            formatted = format_with_citations(resp, max_items=3)
            pretty = pretty_lease_output(formatted)
            return pretty


        except Exception as e:
            debug_log("tool_error", tool="lease_qna", error=str(e))
            return (
                "**Answer**\n"
                f"Sorry—an internal error occurred while retrieving the clause: {e}.\n\n"
                "**Relevant excerpts**\n"
                "• _Tool error; see logs for details._"
            )

    lease_qna = FunctionTool.from_defaults(
        fn=lease_qna_fn,
        name="lease_qna",
        description=(
            "Use for any lease/contract question. Return an answer followed by "
            "‘Relevant excerpts’ with exact clause labels and short verbatim quotes. "
            "If dates/fees must be computed, call date_calculator after this."
        ),
        fn_schema=LeaseQnAInput,
        return_direct=True,
    )

    return lease_qna
