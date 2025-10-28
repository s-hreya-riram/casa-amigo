# utils/utils.py
# ---------------------------------------------------------------------
# Contains async running wrapper for agents parallel workflow to work in streamlit env
# Contains clause formatting for lease qna tool
# Contains geomapping helper functions for answering questions about neighbourhoods
# ---------------------------------------------------------------------
from __future__ import annotations
import re
from textwrap import shorten
from typing import Optional
import asyncio
import re
from textwrap import shorten
from llama_index.core.tools import FunctionTool, ToolMetadata
import math, time, requests
from functools import lru_cache


# -------------- Clause detection & formatting helpers ------------------


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

import re

def pretty_lease_output(raw: str) -> str:
    """
    Take the string from format_with_citations(...) and reflow bullets
    so each '• ...' starts on its own line with consistent spacing.
    """
    # 1. Normalize double spaces after headers
    text = raw.strip()

    # 2. Ensure headers are on their own lines
    text = re.sub(r"\*\*Answer\*\*\s*", "**Answer**\n", text)
    text = re.sub(r"\*\*Relevant excerpts\*\*\s*", "**Relevant excerpts**\n", text)

    # 3. Put each bullet on its own line, and add a blank line between bullets.
    #    We'll turn "• something • something" into:
    #    "• something\n\n• something"
    text = re.sub(r"\s*•\s*", "\n• ", text)  # each bullet starts on new line
    # Now add a blank line between bullets for readability
    # We only add blank lines between consecutive bullets, not before the first.
    text = re.sub(r"\n• (.+?)(?=\n•|\Z)", r"\n• \1\n", text, flags=re.DOTALL)

    # strip trailing whitespace so we don't show extra blank lines at bottom
    return text.strip()



# ------------------ Async workflow runner for sync contexts --------------


async def _run_workflow(workflow, message, memory,  **kwargs):
    return await workflow.run(user_msg=message, memory=memory,  **kwargs)

def run_sync(workflow, message, memory, **kwargs):
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
            return loop.run_until_complete(_run_workflow(workflow, message, memory,  **kwargs))
        elif "no running event loop" in msg:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(_run_workflow(workflow, message, memory,  **kwargs))
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

## ------------------ Geomapping helpers --------------------------------

OSM_USER_AGENT = "CasaAmigo/1.0 (student demo; contact: example@example.com)"  # <-- change

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def minutes_walk(distance_m: float, speed_kmh: float = 4.8) -> int:
    m_per_min = (speed_kmh * 1000) / 60.0
    return max(1, round(distance_m / m_per_min))

@lru_cache(maxsize=256)
def geocode(address: str) -> Optional[tuple[float, float, str]]:
    """Nominatim geocode → (lat, lon, display_name) or None."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}
    r = requests.get(url, params=params, headers={"User-Agent": OSM_USER_AGENT}, timeout=15)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    lat = float(data[0]["lat"]); lon = float(data[0]["lon"])
    return (lat, lon, data[0].get("display_name", address))

import json

def overpass(query: str) -> dict:
    """
    Call Overpass. Always return a dict.
    Never raise.
    On any failure, return {'elements': []} instead of exploding.
    """

    url = "https://overpass-api.de/api/interpreter"

    try:
        resp = requests.post(
            url,
            data={"data": query},
            timeout=10,
            headers={"Accept": "application/json"},
        )
    except Exception as e:
        print("OVERPASS NETWORK ERROR:", e)
        return {"elements": []}  # <- NO RAISE

    # If HTTP not 200, don't raise, just return empty.
    if resp.status_code != 200:
        print("OVERPASS BAD STATUS:", resp.status_code, resp.text[:200])
        return {"elements": []}

    # Try to parse JSON. If broken, return empty.
    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        print("OVERPASS BAD JSON:", e, resp.text[:200])
        return {"elements": []}

    # Guarantee shape
    if not isinstance(data, dict):
        return {"elements": []}
    if "elements" not in data or not isinstance(data["elements"], list):
        data["elements"] = []

    return data

# Map high-level categories → OSM tags
POI_TAGS = {
    "mrt":       [{'key': 'railway', 'val': 'station'}, {'key':'public_transport','val':'station'}],
    "subway":    [{'key': 'railway', 'val': 'station'}],
    "train":     [{'key': 'railway', 'val': 'station'}],
    "bus":       [{'key': 'highway', 'val': 'bus_stop'}],
    "school":    [{'key': 'amenity', 'val': 'school'}],
    "university":[{'key': 'amenity', 'val': 'university'}],
    "hospital":  [{'key': 'amenity', 'val': 'hospital'}],
    "clinic":    [{'key': 'amenity', 'val': 'clinic'}],
    "supermarket":[{'key': 'shop', 'val': 'supermarket'}],
    "park":      [{'key': 'leisure', 'val': 'park'}],
}

""""""

def build_overpass_around(lat: float, lon: float, tags_groups: list[list[dict]], radius_m: int) -> str:
    

    def render_tag_filters(tag_list: list[dict]) -> str:
        parts = []
        for t in tag_list:
            k = t["key"]
            v = t.get("val")
            if v is None:
                parts.append(f'["{k}"]')
            else:
                parts.append(f'["{k}"="{v}"]')
        return "".join(parts)

    clause_lines = []
    for tag_list in tags_groups:
        flt = render_tag_filters(tag_list)
        clause_lines.append(f'  node{flt}(around:{radius_m},{lat},{lon});')
        clause_lines.append(f'  way{flt}(around:{radius_m},{lat},{lon});')
        clause_lines.append(f'  relation{flt}(around:{radius_m},{lat},{lon});')

    query = f"""
[out:json][timeout:30];
(
{chr(10).join(clause_lines)}
);
out center 20;
""".strip()

    return query



def osm_url(elem: dict) -> str:
    et = elem.get("type", "node")
    eid = elem.get("id")
    return f"https://www.openstreetmap.org/{et}/{eid}"
