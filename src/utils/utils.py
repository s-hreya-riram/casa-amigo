import asyncio
import re
from textwrap import shorten
from llama_index.core.tools import FunctionTool, ToolMetadata

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
