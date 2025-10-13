from typing import List, Optional
import re
from textwrap import shorten
from pydantic import BaseModel

from llama_index.core import VectorStoreIndex
from llama_index.core.tools import FunctionTool
from utils.utils import format_with_citations, detect_clause_label_from_text

# ---- in-memory debug list for UI --------------------------
_DEBUG_LOG: list[dict] = []

def debug_log(event: str, **kwargs):
    _DEBUG_LOG.append({"event": event, **kwargs})

def consume_debug_log() -> list[dict]:
    """UI can call this to read & clear the buffer each turn."""
    out = list(_DEBUG_LOG)
    _DEBUG_LOG.clear()
    return out

# ---- TODO tools ----------------------------------------------------
def date_calculator(): ...
def dimension_calculator(): ...
def notification_workflow(): ...
def personalised_recommendation(): ...
def neighbourhood_researcher(): ...


# ---- Tool registry ---------------------------------------------------------

def build_tools(index: VectorStoreIndex, similarity_top_k: int = 5):
    # Keep k modest for precision; you can raise to 8–12 if needed
    qe = index.as_query_engine(similarity_top_k=similarity_top_k, response_mode="compact")

    class LeaseQnAInput(BaseModel):
        input: str  # required by the agent tool-calling schema

    def lease_qna_fn(input: str) -> str:
        """Lease/contract Q&A with clause citations, formatted for the report."""
        debug_log("tool_called", tool="lease_qna", args={"input": input})
        try:
            resp = qe.query(input)
            sns = getattr(resp, "source_nodes", []) or []

            # collect top-3 for the UI debug panel
            top3 = []
            for i, sn in enumerate(sns[:3]):
                meta = (getattr(sn.node, "metadata", {}) or {})
                label = (
                    (f"Clause {meta.get('clause_num')}: {meta.get('clause_title')}")
                    if meta.get("clause_num") or meta.get("clause_title")
                    else detect_clause_label_from_text(sn.node.text or "")
                ) or (f"Page {meta.get('page_label') or meta.get('page')}")
                top3.append({"rank": i, "score": getattr(sn, "score", None), "label": label})

            debug_log("retrieval", tool="lease_qna",
                      retrieved_k=len(sns),
                      top=top3)

            # low-confidence guard (avoid generic answers)
            top_score = getattr(sns[0], "score", None) if sns else None
            if top_score is not None and top_score < 0.2:
                return ("**Answer**\n"
                        "I couldn’t confidently find a matching clause in your lease. "
                        "Could you specify the clause number/title or share the relevant page?\n\n"
                        "**Relevant excerpts**\n"
                        "• _No clearly relevant clauses above the confidence threshold._")

            return format_with_citations(resp)

        except Exception as e:
            debug_log("tool_error", tool="lease_qna", error=str(e))
            return ("**Answer**\n"
                    "Sorry—an internal error occurred while retrieving the clause.\n\n"
                    "**Relevant excerpts**\n"
                    "• _Tool error; see logs for details._")

    lease_qna = FunctionTool.from_defaults(
        fn=lease_qna_fn,
        name="lease_qna",
        description=("Use for any lease/contract question. Return an answer followed by "
                     "‘Relevant excerpts’ with exact clause labels and short verbatim quotes. "
                     "If dates/fees must be computed, call date_calculator after this."),
        fn_schema=LeaseQnAInput,
    )

    date_calc_tool = FunctionTool.from_defaults(
        fn=date_calculator,
        name="date_calculator",
        description=("Deterministic calculator for notice periods, last day, proration, late fees. "
                     "Inputs: ISO dates (YYYY-MM-DD), currency in SGD; use after lease_qna."),
    )
    neighborhood_tool = FunctionTool.from_defaults(
        fn=neighbourhood_researcher,
        name="neighborhood_researcher",
        description=("Locality info: MRT/schools proximity, commute times, amenities, reviews."),
    )
    fit_tool = FunctionTool.from_defaults(
        fn=dimension_calculator,
        name="fit_checker",
        description=("Spatial check for furniture/door/room; returns pass/fail and limiting step."),
    )
    workflow_tool = FunctionTool.from_defaults(
        fn=notification_workflow,
        name="workflow_helper",
        description=("Creates reminders, viewing emails, and checklists."),
    )
    persona_tool = FunctionTool.from_defaults(
        fn=personalised_recommendation,
        name="persona_ranker",
        description=("Builds a user persona and scores candidate listings with an audit trail."),
    )

    return [lease_qna, date_calc_tool, neighborhood_tool, fit_tool, workflow_tool, persona_tool]
