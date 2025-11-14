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

OSM_USER_AGENT = "CasaAmigo/1.0 (+github.com/s-hreya-riram/casa-amigo; shreyasriram29@gmail.com)"

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

import time

def overpass(query: str, max_retries: int = 3) -> dict:
    """
    Call Overpass with retry logic.
    Always return a dict, never raise.
    """
    url = "https://overpass-api.de/api/interpreter"

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                url,
                data={"data": query},
                timeout=30,
                headers={
                    "Accept": "application/json",
                    "User-Agent": OSM_USER_AGENT,  # Add this!
                },
            )
            
            # If HTTP not 200, retry
            if resp.status_code != 200:
                print(f"OVERPASS BAD STATUS (attempt {attempt+1}): {resp.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
                return {"elements": []}

            # Try to parse JSON
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                print(f"OVERPASS BAD JSON (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {"elements": []}

            # Guarantee shape
            if not isinstance(data, dict):
                return {"elements": []}
            if "elements" not in data or not isinstance(data["elements"], list):
                data["elements"] = []

            return data

        except requests.exceptions.Timeout as e:
            print(f"OVERPASS TIMEOUT (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"elements": []}
        
        except Exception as e:
            print(f"OVERPASS NETWORK ERROR (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return {"elements": []}

    return {"elements": []}
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

from textwrap import shorten  # if not already imported

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

import re
from textwrap import shorten

import re

def _strip_clause_prefix(quote: str) -> str:
    """
    Remove leading 'Clause 5:', 'Clause 5(c):', etc. from a snippet so we don't
    show the clause number twice.
    """
    if not quote:
        return quote
    # e.g. "Clause 5: PROVIDED ALWAYS ..." or "Clause 5(c): ..."
    return re.sub(
        r"^\s*Clause\s+[0-9A-Za-z()]+[:.\-–]?\s*",
        "",
        quote,
        count=1,
    )


def excerpt(text: str, width: int = 320) -> str:
    """Collapse whitespace, fix OCR jammed words, and shorten with an ellipsis."""
    s = text or ""
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    return shorten(s, width=width, placeholder="…")


CLAUSE_SHORT_RE = re.compile(r"\bClause\s+(\d+(?:\([a-z]\))?)", re.I)

def _short_clause_label(label: str) -> str:
    if not label:
        return "Clause (unspecified)"
    m = CLAUSE_SHORT_RE.search(label)
    if m:
        # Gives "Clause 5" or "Clause 5(c)"
        return f"Clause {m.group(1)}"
    return label


def format_with_citations(resp, min_items: int = 1, max_items: int = 3) -> str:
    answer_text = resp.response if getattr(resp, "response", None) else str(resp)
    answer_text = (answer_text or "").strip()

    lines = [
        "**Answer**",
        answer_text,
        "",
        "**Relevant excerpts**",
    ]

    seen_labels = set()
    count = 0

    for sn in (getattr(resp, "source_nodes", []) or []):
        if count >= max_items:
            break

        node = sn.node
        meta = getattr(node, "metadata", {}) or {}

        clause_label = meta.get("clause_label")
        clause_num   = meta.get("clause_num")
        clause_title = meta.get("clause_title")
        page         = meta.get("page_label") or meta.get("page")

        # Build a human-readable label
        label = None
        if clause_label and clause_title:
            label = f"Clause {clause_label}: {clause_title}"
        elif clause_label:
            label = f"Clause {clause_label}"
        elif clause_num and clause_title:
            label = f"Clause {clause_num}: {clause_title}"
        elif clause_title:
            label = clause_title

        if not label:
            label = detect_clause_label_from_text(node.text or "")
        if not label:
            label = f"Page {page}" if page is not None else "Clause (unspecified)"

        short_label = _short_clause_label(label)

        # Dedup by short label so we don't repeat the same clause
        if short_label in seen_labels:
            continue
        seen_labels.add(short_label)

        # Create the excerpt body
        raw_quote = excerpt(node.text or "")
        quote_body = _strip_clause_prefix(raw_quote)

        combined = f"{quote_body} ({short_label})"

        # single blockquote line; pretty_lease_output will wrap it in grey
        lines.append(f"> {combined}")
        lines.append("")
        count += 1

    if count < min_items:
        lines.append("> _No clearly relevant clauses were found above the confidence threshold._")

    return "\n".join(lines).strip()


def pretty_lease_output(raw: str) -> str:
    """
    Convert our markdown-ish answer into HTML suitable for the UI.
    - Removes the "**Answer**" heading
    - Renders "Relevant excerpts from your lease:" header
    - Turns each pair of blockquote lines into a styled <blockquote>
    """
    text = (raw or "").strip()

    # 1. Remove the "**Answer**" prefix.
    text = re.sub(
        r"\*\*Answer\*\*[:\s]*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # 2. Replace "**Relevant excerpts**" with styled HTML heading.
    text = re.sub(
        r"\*\*Relevant excerpts\*\*[: ]*\n?",
        "<br><br>"
        "<div style='font-size:0.95em; font-weight:600; color:#000;'>"
        "Relevant excerpts from your lease:"
        "</div>"
        "<br>\n",   # <-- ensure the first '>' starts on a new line
        text,
        flags=re.IGNORECASE,
    )


    
    # 3. Convert markdown blockquotes into HTML blockquotes.
    lines = text.splitlines()
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # treat any variant of ">...", "> …", ">   …" as a blockquote
        if stripped.startswith(">"):
            body = stripped[1:].lstrip()   # drop ">" and any spaces
            quote = body
            label = ""

            # Backwards-compat: if the *next* line is also a blockquote,
            # treat it as the label line.
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].lstrip()
                if next_stripped.startswith(">"):
                    label = next_stripped[1:].lstrip()
                    i += 1  # consume label line

            block = (
                "<blockquote style='border-left:3px solid #ddd; padding-left:12px; "
                "margin:8px 0; font-size:0.95em;'>"
                f"{quote}"
                + (f"<br><span style='font-style:italic;'>{label}</span>" if label else "")
                + "</blockquote>"
            )
            new_lines.append(block)
        else:
            new_lines.append(line)
        i += 1

    text = "\n".join(new_lines)

    # 4. Keep old bullet logic just in case there are '•'
    text = re.sub(r"\s*•\s*", "<br>• ", text)

    # 5. Bold 'Clause X:' or 'Page Y:' if they appear in bullets/plain text
    text = re.sub(
        r"(•\s*)(Clause\s*\d+[A-Za-z0-9() ]*?:)",
        r"\1<b>\2</b>",
        text,
    )
    text = re.sub(
        r"(•\s*)(Page\s*\d+[A-Za-z0-9() ]*?:)",
        r"\1<b>\2</b>",
        text,
    )

    # 6. Collapse excessive <br>
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
