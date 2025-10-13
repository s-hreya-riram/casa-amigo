from typing import List
from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata
from llama_index.core import VectorStoreIndex
from pydantic import BaseModel
from textwrap import shorten



def date_calculator():
    pass

def dimension_calculator():
    pass

def notification_workflow():
    pass

def personalised_recommendation(): 
    pass

def neighbourhood_researcher():
    pass

import re
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode, MetadataMode

def _excerpt(txt: str, width: int = 320) -> str:
    txt = re.sub(r"\s+", " ", txt).strip()
    return shorten(txt, width=width, placeholder="…")

def _format_with_citations(resp, min_items: int = 1) -> str:
    """Make: Answer + Relevant excerpts with (Clause N: Title) labels."""
    # 1) main answer text
    if hasattr(resp, "response") and isinstance(resp.response, str):
        answer_text = resp.response
    else:
        answer_text = str(resp)

    lines = ["**Answer**", answer_text, "", "**Relevant excerpts**"]
    seen = set()
    count = 0

    for sn in getattr(resp, "source_nodes", []) or []:
        node = sn.node
        meta = getattr(node, "metadata", {}) or {}
        # Prefer clause metadata if you added it during ingest
        clause_num = meta.get("clause_num")
        clause_title = meta.get("clause_title")
        page = meta.get("page_label") or meta.get("page")  # fallback

        if clause_num or clause_title:
            label = f"Clause {clause_num}: {clause_title}" if clause_num else f"{clause_title}"
        elif page is not None:
            label = f"Page {page}"
        else:
            label = "Clause (unspecified)"

        key = (label, node.text[:80])
        if key in seen:
            continue
        seen.add(key)

        quote = _excerpt(node.text)
        lines.append(f"• *{label}* — “{quote}”")
        count += 1

    if count < min_items:
        lines.append("• _No clearly relevant clauses were found above the confidence threshold._")

    return "\n".join(lines)


def build_tools(index: VectorStoreIndex, similarity_top_k: int = 5):
    
    # RAG query engine with citation formatting as per professor sample response
    qe = index.as_query_engine(similarity_top_k=similarity_top_k, response_mode="compact")

    class LeaseQnAInput(BaseModel):
        input: str  # single required field

    def lease_qna_fn(input: str) -> str:
        """Answer lease/contract questions with clause citations formatted for the report."""
        resp = qe.query(input)
        return _format_with_citations(resp)

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
        description=("Deterministic calculator for notice periods, last day of tenancy, proration, late fees. "
                     "Inputs: ISO dates (YYYY-MM-DD), currency in SGD. Use after lease_qna reveals the rules.")
    )

    neighborhood_tool = FunctionTool.from_defaults(
        fn=neighbourhood_researcher,
        name="neighborhood_researcher",
        description=("External locality info: MRT/schools proximity, commute times, amenities, reviews. "
                     "Use for area/market questions, not contract terms.")
    )

    fit_tool = FunctionTool.from_defaults(
        fn=dimension_calculator,
        name="fit_checker",
        description=("Spatial check for furniture vs door/room. Dimensions in cm. "
                     "Returns pass/fail plus limiting step (door width, diagonal turn, corridor).")
    )

    workflow_tool = FunctionTool.from_defaults(
        fn=notification_workflow,
        name="workflow_helper",
        description=("Creates checklists, reminder schedules, viewing emails/notes. Use when the user asks to schedule/share/export.")
    )

    persona_tool = FunctionTool.from_defaults(
        fn=personalised_recommendation,
        name="persona_ranker",
        description=("Builds a persona profile (noise sensitivity, commute max, greenery preference, budget) "
                     "and scores candidate listings with an audit trail.")
    )

    return [lease_qna, date_calc_tool, neighborhood_tool, fit_tool, workflow_tool, persona_tool]
