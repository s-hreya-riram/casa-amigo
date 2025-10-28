from utils.utils import geocode, overpass, build_overpass_around, haversine_m, minutes_walk, osm_url, POI_TAGS 

# ------ Neighborhood researcher tool ----------------------------------------
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

    #debug_log("tool_called", tool="neighborhood_researcher",args={"address": address, "poi": poi, "radius_m": radius})

    # ---- step 3: ------ call overpass API to get the nearby amenities
    tags = POI_TAGS.get(poi) or [{'key': 'amenity', 'val': poi}]
    if isinstance(tags, list) and tags and isinstance(tags[0], dict):
        tags_groups = [[t] for t in tags]   # e.g. [{'key':..}, {'key':..}] -> [[{..}], [{..}]]
    else:
        tags_groups = [tags] if tags else []
    try:
        q = build_overpass_around(lat, lon, tags_groups, radius)
        data = overpass(q)
        #debug_log("overpass_query_summary", summary=q)

        data = overpass(q)
        elements = data.get("elements", [])
    except Exception as e:
        #debug_log("tool_error", tool="neighborhood_researcher", error=str(e))
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

    #debug_log("retrieval", tool="neighborhood_researcher",retrieved_k=len(rows),top=[{"rank": i, "score": None, "label": f"{r['name']} ({r['distance_m']} m)"} for i, r in enumerate(top)])

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
        f"Here are the closest {poi} options near {disp} (within {radius} m):\n\n"
        + "\n".join(lines)
        + "\n\n**Data sources**\n"
        "- OpenStreetMap / Overpass; distances are straight-line, walking time is estimated."
    )

