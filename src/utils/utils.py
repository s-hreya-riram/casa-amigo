# utils/utils.py
# ---------------------------------------------------------------------
# Contains async running wrapper for agents parallel workflow to work in streamlit env
# Contains geomapping helpers for neighbourhood researcher
# Contains text clause formatting for lease qna tool
# ---------------------------------------------------------------------
from __future__ import annotations
import re
from textwrap import shorten
from typing import Optional
import asyncio
import math, requests
from functools import lru_cache
import re
from bs4 import BeautifulSoup  # if you already use bs4 elsewhere; if not, you can make this optional



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

# ------------------ Lease clause formatting helpers ----------------------

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



def pretty_lease_output(raw: str) -> str:
    """
    Format lease_qna output as HTML for UI rendering.
    Assumes the UI will render with unsafe_allow_html=True / dangerouslySetInnerHTML.
    """
    text = raw.strip()

    # 1. Remove the "**Answer**" prefix completely.
    text = re.sub(
        r"\*\*Answer\*\*[:\s]*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # 2. Replace "**Relevant excerpts**" with a styled subheading + spacing.
    #    We insert <br><br> above and below to force visual separation.
    text = re.sub(
        r"\*\*Relevant excerpts\*\*[:\s]*",
        "<br><br>"
        "<div style='font-size:0.95em; font-weight:600; color:#000;'>"
        "Relevant excerpts from your lease:"
        "</div>"
        "<br>",
        text,
        flags=re.IGNORECASE,
    )

    # 3. Strip raw markdown emphasis chars from the lease text
    #    (the OCR/pdf often leaves random * and _ that render as italics or squished text).
    text = re.sub(r"[*_]{1,2}", "", text)

    # 4. Put each bullet on its own line in HTML.
    #    We'll turn any inline " • " into "<br>• ".
    text = re.sub(r"\s*•\s*", "<br>• ", text)

    # 5. Bold only the clause/page labels after the bullet.
    #    Example: • Clause 200: ... → • <b>Clause 200:</b> ...
    text = re.sub(
        r"(•\s*)(Clause\s*\d+[^:]*:)",
        r"\1<b>\2</b>",
        text,
    )
    text = re.sub(
        r"(•\s*)(Page\s*\d+[^:]*:)",
        r"\1<b>\2</b>",
        text,
    )

    # 6. Collapse any triple <br> down to double so spacing isn't huge.
    text = re.sub(r"(<br>\s*){3,}", "<br><br>", text)

    # 7. Trim leading/trailing whitespace/br
    text = text.strip()
    text = re.sub(r"^(<br>\s*)+", "", text)
    text = re.sub(r"(<br>\s*)+$", "", text)

    return text

def clean_pdf_fragments(raw: str) -> str:
    if not raw:
        return raw

    # 1) strip any stray HTML tags your pipeline kept
    try:
        raw = BeautifulSoup(raw, "html.parser").get_text(separator=" ")
    except Exception:
        # if bs4 not available, just fall back
        pass

    # 2) fix cases where words get jammed together around clause letters
    # e.g. "...to be borne by the Tenantandthe excess..." → insert space before capital
    raw = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', raw)

    # 3) collapse crazy whitespace
    raw = re.sub(r'\s+', ' ', raw)

    return raw.strip()



#### ----- for reminder_tool.py: timezone conversion helper -------

from datetime import datetime, timezone
import zoneinfo  # built-in in 3.9+

SG_TZ = zoneinfo.ZoneInfo("Asia/Singapore")

def to_utc_iso(sgt_dt_str: str) -> str:
    """
    Take a naive datetime string the LLM gave us (assume it's SGT),
    make it timezone-aware (Asia/Singapore), then convert to UTC,
    and return ISO string for the API.
    """
    # 1) parse what the model gave (no tz)
    dt_naive = datetime.fromisoformat(sgt_dt_str)  # e.g. "2025-10-31T12:33:00"

    # 2) say "this is SGT"
    dt_sgt = dt_naive.replace(tzinfo=SG_TZ)

    # 3) convert to UTC
    dt_utc = dt_sgt.astimezone(timezone.utc)

    # 4) return ISO for API
    return dt_utc.isoformat(timespec="seconds")
