from utils.utils import geocode, overpass, build_overpass_around, haversine_m, minutes_walk, osm_url, POI_TAGS 

from pydantic import BaseModel, Field

class NeighborhoodInput(BaseModel):
    """Input schema for neighborhood researcher tool."""
    address: str = Field(
        description="Full address to search from (e.g., '2 Indus Road' or '123 Orchard Road, Singapore')"
    )
    poi: str = Field(
        description="Type of amenity to search for (e.g., 'mrt', 'supermarket', 'hospital', 'school', 'park')"
    )

# ------ Neighborhood researcher tool ----------------------------------------
def neighborhood_researcher(address: str, poi: str) -> str:
    # Defensive checks
    if not address or not isinstance(address, str):
        return "❌ Error: No address provided."
    
    if not poi or not isinstance(poi, str):
        return "❌ Error: No amenity type provided."
    
    print(f"[DEBUG] Received address='{address}', poi='{poi}'")
    
    # Step 1: Ensure Singapore
    if "singapore" not in address.lower():
        address = address + ", Singapore"
    
    # Step 2: Geocode with detailed error handling
    print(f"[DEBUG] Geocoding: {address}")
    
    try:
        g = geocode(address)
        print(f"[DEBUG] Geocode returned: type={type(g)}, value={g}")  # ← Add this
    except Exception as e:
        print(f"[DEBUG] Geocode exception: {type(e).__name__}: {e}")
        return f"❌ Geocoding failed: {str(e)}"
    
    if g is None:
        print(f"[DEBUG] Geocode returned None")
        return f"❌ Could not find the address: {address}"
    
    # Add validation
    if not isinstance(g, tuple) or len(g) != 3:
        print(f"[DEBUG] Geocode returned invalid format: {g}")
        return f"❌ Geocoding returned unexpected format: {type(g)}"
    
    try:
        lat, lon, disp = g
        print(f"[DEBUG] Unpacked: lat={lat}, lon={lon}, disp={disp}")
    except Exception as e:
        print(f"[DEBUG] Unpacking failed: {e}")
        return f"❌ Could not parse geocoding result: {g}"
    
    # Step 3: POI synonyms
    synonyms = {
        "metro": "mrt", "subway": "mrt", "train": "mrt",
        "schools": "school", "uni": "university",
        "clinics": "clinic", "hospitals": "hospital",
        "markets": "supermarket",
    }
    poi = synonyms.get(poi, poi)
    radius = 1200
    print(f"[DEBUG] Searching for {poi} within {radius}m")

    # Step 4: Build Overpass query
    tags = POI_TAGS.get(poi) or [{'key': 'amenity', 'val': poi}]
    if isinstance(tags, list) and tags and isinstance(tags[0], dict):
        tags_groups = [[t] for t in tags]
    else:
        tags_groups = [tags] if tags else []
    
    print(f"[DEBUG] Building Overpass query for tags: {tags_groups}")
    q = build_overpass_around(lat, lon, tags_groups, radius)
    print(f"[DEBUG] Overpass query built, length: {len(q)}")
    
    # Step 5: Call Overpass
    print(f"[DEBUG] Calling Overpass API...")
    data = overpass(q)
    print(f"[DEBUG] Overpass response received: {type(data)}")
    
    elements = data.get("elements", [])
    print(f"[DEBUG] Overpass returned {len(elements)} elements")

    # Step 6: Calculate distances
    rows = []
    for e in elements:
        center = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        if center.get("lat") is None or center.get("lon") is None:
            continue
        d = haversine_m(lat, lon, center["lat"], center["lon"])
        name = (e.get("tags", {}) or {}).get("name") or "(unnamed)"
        rows.append({
            "name": name, 
            "distance_m": int(d), 
            "walk_min": minutes_walk(d), 
            "url": osm_url(e)
        })
    
    print(f"[DEBUG] Processed {len(rows)} valid results")
    
    rows.sort(key=lambda r: r["distance_m"])
    clean_rows = [r for r in rows if r["name"] != "(unnamed)"]
    top = clean_rows[:5]
    
    print(f"[DEBUG] Top {len(top)} results after filtering")

    # Step 7: Format response
    if not top:
        result = (
            f"**Answer**\n"
            f"No {poi} was found within {radius} m of {disp}.\n\n"
            f"**Data sources**\n"
            f"- OpenStreetMap / Overpass distance calc"
        )
        print(f"[DEBUG] Returning empty result")
        return result

    lines = []
    for r in top:
        lines.append(
            f"- {r['name']} — {r['distance_m']} m (~{r['walk_min']} min walk)\n  {r['url']}"
        )

    result = (
        f"Here are the closest {poi} options near {disp} (within {radius} m):\n\n"
        + "\n".join(lines)
        + "\n\n**Data sources**\n"
        "- OpenStreetMap / Overpass; distances are straight-line, walking time is estimated."
    )
    
    print(f"[DEBUG] Returning success result, length: {len(result)}")
    return result