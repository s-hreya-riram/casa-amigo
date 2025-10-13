# utils/utils.py
# ---------------------------------------------------------------------
# Contains async running wrapper for agents parallel workflow to work in streamlit env
# Contains clause formatting for lease qna tool
# ---------------------------------------------------------------------
from __future__ import annotations
import re
from textwrap import shorten
from typing import Optional
import asyncio
import re
from textwrap import shorten
from llama_index.core.tools import FunctionTool, ToolMetadata


# Try to match common clause header styles:
#  1) "8. Diplomatic Clause", "8.2 Early Termination", "8(b) ..."
#  2) "Clause 8(b): Diplomatic Clause"
#  3) "Special Clause: Diplomatic Clause"
#  4) Named only: "Diplomatic Clause"
CLAUSE_HEADER_RE = re.compile(
    r"""(?imx)
    ^
    (?:
        \s*(?:Clause\s*)?
        (?P<num>\d+(?:\.\d+)*(?:\([a-zA-Z]\))?)
        [\s.:–-]+
        (?P<title>[A-Za-z][^\n]{0,80})
      |
        \s*Special\s+Clause[\s.:–-]+
        (?P<title_only>[A-Za-z][^\n]{0,80})
      |
        \s*(?P<named>(?:Diplomatic|Break|Early\s+Termination)\s+Clause)
    )
    """
)

def detect_clause_label_from_text(text: str) -> Optional[str]:
    """Return a nice 'Clause X: Title' label by parsing `text` if metadata is missing."""
    if not text:
        return None
    m = CLAUSE_HEADER_RE.search(text)
    if not m:
        return None
    num = m.groupdict().get("num")
    title = m.groupdict().get("title")
    title_only = m.groupdict().get("title_only")
    named = m.groupdict().get("named")
    if num and title:
        return f"Clause {num}: {title.strip(' -–:')[:80]}"
    if title_only:
        return f"Special Clause: {title_only.strip(' -–:')[:80]}"
    if named:
        return named
    return None

def excerpt(text: str, width: int = 320) -> str:
    """Collapse whitespace and shorten with an ellipsis."""
    return shorten(re.sub(r"\s+", " ", text or "").strip(), width=width, placeholder="…")

def format_with_citations(resp, min_items: int = 1) -> str:
    """Return 'Answer' + 'Relevant excerpts' with clause labels when available."""
    answer_text = resp.response if getattr(resp, "response", None) else str(resp)
    lines = ["**Answer**", answer_text, "", "**Relevant excerpts**"]

    seen = set()
    count = 0
    for sn in getattr(resp, "source_nodes", []) or []:
        node = sn.node
        meta = (getattr(node, "metadata", {}) or {})
        clause_num = meta.get("clause_num")
        clause_title = meta.get("clause_title")
        page = meta.get("page_label") or meta.get("page")

        label = None
        if clause_num or clause_title:
            label = f"Clause {clause_num}: {clause_title}" if clause_num else clause_title
        if not label:
            label = detect_clause_label_from_text(node.text or "")
        if not label:
            label = f"Page {page}" if page is not None else "Clause (unspecified)"

        key = (label, (node.text or "")[:80])
        if key in seen:
            continue
        seen.add(key)

        lines.append(f"• *{label}* — “{excerpt(node.text)}”")
        count += 1

    if count < min_items:
        lines.append("• _No clearly relevant clauses were found above the confidence threshold._")

    return "\n".join(lines)

async def _run_workflow(workflow, message, memory):
    return await workflow.run(user_msg=message, memory=memory)

def run_sync(workflow, message, memory):
    try:
        return asyncio.run(_run_workflow(workflow, message, memory))
    except RuntimeError as e:
        msg = str(e)
        if "asyncio.run() cannot be called from a running event loop" in msg:
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except Exception:
                pass
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(_run_workflow(workflow, message, memory))
        elif "no running event loop" in msg:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(_run_workflow(workflow, message, memory))
            finally:
                loop.close()
        else:
            raise

def extract_text(agent_output) -> str:
    """
    Normalize AgentWorkflow outputs to a plain string for simple chat UIs.
    """
    out = agent_output
    # AgentOutput.response.message.content -> [TextBlock(...)]
    if hasattr(out, "response") and hasattr(out.response, "message"):
        content = getattr(out.response.message, "content", None)
        if isinstance(content, list) and content:
            block = content[0]
            # TextBlock has .text
            if hasattr(block, "text"):
                return block.text
    # Some versions expose .response as str or have .content as list/str
    if hasattr(out, "response"):
        resp = out.response
        if isinstance(resp, str):
            return resp
        if hasattr(resp, "content"):
            c = resp.content
            if isinstance(c, list) and c:
                b0 = c[0]
                if hasattr(b0, "text"):
                    return b0.text
            return str(c)
    return str(out)

