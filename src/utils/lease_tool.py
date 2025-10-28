# -------------- Clause detection & formatting helpers ------------------
from __future__ import annotations
from pydantic import BaseModel
from llama_index.core import VectorStoreIndex
from llama_index.core.tools import FunctionTool
from utils.utils import detect_clause_label_from_text, format_with_citations, pretty_lease_output

class LeaseQnAInput(BaseModel):
        input: str

def build_lease_qna_tool(index: VectorStoreIndex, debug_log):
    """Return the Lease Q&A FunctionTool using the provided VectorStoreIndex."""
    qe = index.as_query_engine(similarity_top_k=5, response_mode="compact")

    

    def lease_qna_fn(input: str) -> str:
        """Lease/contract Q&A with clause citations, formatted for the report."""
        debug_log("tool_called", tool="lease_qna", args={"input": input})
        try:
            resp = qe.query(input)
            sns = getattr(resp, "source_nodes", []) or []

            top3 = []
            for i, sn in enumerate(sns[:3]):
                meta = getattr(sn.node, "metadata", {}) or {}
                label = (
                    (f"Clause {meta.get('clause_num')}: {meta.get('clause_title')}")
                    if meta.get("clause_num") or meta.get("clause_title")
                    else detect_clause_label_from_text(sn.node.text or "")
                ) or (f"Page {meta.get('page_label') or meta.get('page')}")
                top3.append({"rank": i, "score": getattr(sn, "score", None), "label": label})

            debug_log("retrieval", tool="lease_qna", retrieved_k=len(sns), top=top3)

            top_score = getattr(sns[0], "score", None) if sns else None
            if top_score is not None and top_score < 0.2:
                return (
                    "**Answer**\n"
                    "I couldn’t confidently find a matching clause in your lease. "
                    "Could you specify the clause number/title or share the relevant page?\n\n"
                    "**Relevant excerpts**\n"
                    "• _No clearly relevant clauses above the confidence threshold._"
                )

            formatted = format_with_citations(resp)
            pretty = pretty_lease_output(formatted)
            return pretty

        except Exception as e:
            debug_log("tool_error", tool="lease_qna", error=str(e))
            return (
                "**Answer**\n"
                "Sorry—an internal error occurred while retrieving the clause.\n\n"
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
