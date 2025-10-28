from typing import List, Optional
import re
from typing import Union
from textwrap import shorten
from pydantic import BaseModel, Field

from llama_index.core import VectorStoreIndex
from llama_index.core.tools import FunctionTool
from utils.utils import format_with_citations, detect_clause_label_from_text

from utils.utils import format_with_citations, pretty_lease_output,geocode, overpass, build_overpass_around, haversine_m, minutes_walk, osm_url, POI_TAGS  # (still used by lease tool)

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



   
#--- Neighborhood researcher tool ----------------------------------------
def neighborhood_researcher(address: str, poi: str) -> str:


    # ---- step 1: ------ ensure its only for singapore ( else wont work )
    if "singapore" not in address.lower():
        address = address + ", Singapore"
    else:
        address = address

    # ---- step 2: ------ setup latitude/longitude/formatted address
    g = geocode(address) # (51.4751259, 0.0346723, '2, Indus Road, Charlton, Royal Borough of Greenwich, London, Greater London, England, SE7 7DA, United Kingdom')
    lat, lon, disp = g

    synonyms = {
        "metro": "mrt", "subway": "mrt", "train": "mrt",
        "schools": "school", "uni": "university",
        "clinics": "clinic", "hospitals": "hospital",
        "markets": "supermarket",
    }
    poi = synonyms.get(poi, poi)

    radius = 1200

    debug_log("tool_called", tool="neighborhood_researcher",
              args={"address": address, "poi": poi, "radius_m": radius})

    # ---- step 3: ------ call overpass API to get the nearby amenities
    tags = POI_TAGS.get(poi) or [{'key': 'amenity', 'val': poi}]
    if isinstance(tags, list) and tags and isinstance(tags[0], dict):
        tags_groups = [[t] for t in tags]   # e.g. [{'key':..}, {'key':..}] -> [[{..}], [{..}]]
    else:
        tags_groups = [tags] if tags else []
    try:
        q = build_overpass_around(lat, lon, tags_groups, radius)
        data = overpass(q)
        debug_log("overpass_query_summary", summary=q)

        data = overpass(q)
        elements = data.get("elements", [])
    except Exception as e:
        debug_log("tool_error", tool="neighborhood_researcher", error=str(e))
        return f"Sorry—there was a network error while checking nearby amenities. Please try again. {q}"

    # ----- step 4: ----- get the distances and format results
    rows = []
    for e in elements:
        center = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        if center["lat"] is None or center["lon"] is None:
            continue
        d = haversine_m(lat, lon, center["lat"], center["lon"])
        name = (e.get("tags", {}) or {}).get("name") or "(unnamed)"
        rows.append({"name": name, "distance_m": int(d), "walk_min": minutes_walk(d), "url": osm_url(e)})
    rows.sort(key=lambda r: r["distance_m"])

    clean_rows = [r for r in rows if r["name"] != "(unnamed)"]
    clean_rows.sort(key=lambda r: r["distance_m"])
    top = clean_rows[:5]

    debug_log("retrieval", tool="neighborhood_researcher",
              retrieved_k=len(rows),
              top=[{"rank": i, "score": None, "label": f"{r['name']} ({r['distance_m']} m)"} for i, r in enumerate(top)])

    if not top:
        return (
            "**Answer**\n"
            f"No {poi} was found within {radius} m of {disp}.\n\n"
            "**Data sources**\n"
            "- OpenStreetMap / Overpass distance calc (walking time is straight-line distance / ~80 m per min)"
        )

    lines = []
    for r in top:
        lines.append(
            f"- {r['name']} — {r['distance_m']} m (~{r['walk_min']} min walk)\n  {r['url']}"
        )

    return (
        "**Answer**\n"
        f"Here are the closest {poi} options near {disp} (within {radius} m):\n\n"
        + "\n".join(lines)
        + "\n\n**Data sources**\n"
        "- OpenStreetMap / Overpass; distances are straight-line, walking time is estimated."
    )


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

            #return format_with_citations(resp)
            formatted = format_with_citations(resp)
            pretty = pretty_lease_output(formatted)
            return pretty

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
        return_direct=True, 
    )

    date_calc_tool = FunctionTool.from_defaults(
        fn=date_calculator,
        name="date_calculator",
        description=("Deterministic calculator for notice periods, last day, proration, late fees. "
                     "Inputs: ISO dates (YYYY-MM-DD), currency in SGD; use after lease_qna."),
    )
    """
    neighborhood_tool = FunctionTool.from_defaults(
        fn=neighbourhood_researcher,
        name="neighborhood_researcher",
        description=("Find nearby amenities (MRT, schools, hospitals, parks, supermarkets, etc.) "
                 "around a given address. Returns top results with distance & an OSM link."),
        fn_schema=NeighborhoodInput,
        return_direct=True, 
    )
    """
    neighborhood_tool = FunctionTool.from_defaults(
        fn=neighborhood_researcher,
        name="neighborhood_researcher",
        description="Return dummy walk distance to MRT. Input: any string address.",
        return_direct=True,
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
