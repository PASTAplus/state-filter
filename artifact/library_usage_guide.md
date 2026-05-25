# Library Integration Guide - State-Filter

This document outlines how to programmatically use the `state-filter` package as a library within other Python applications, bypass the CLI, and interact directly with the geospatial and data retrieval APIs.

---

## 📦 Exposed API Interface

All public-facing methods are exposed directly at the package root via standard imports. You do not need to query submodules like `geo` or `pasta` directly.

### Core Exposed Functions

* `load_state_geometry(state_name: str) -> BaseGeometry`
  * Resolves and merges US state geometries from the bundled GeoJSON. Returns a Shapely `Polygon` or `MultiPolygon` with topological self-intersections automatically repaired.
* `search_and_filter_all(state_name: str, semantic_options: dict, state_geometry: BaseGeometry, mode: str) -> list[str]`
  * Performs automatic, paginated Solr search operations over the EDI PASTA API and filters results using Shapely containment/intersection testing.
* `load_state_bbox(state_name: str) -> dict[str, float]`
  * Returns the pre-computed Solr spatial range limits mapping `{"minLon", "maxLon", "maxLat", "minLat"}`.
* `validate_coordinates(lon: float, lat: float) -> bool`
  * Validates decimal coordinates boundaries range checking.

---

## 💻 Code Example

Here is a complete integration script showing how to load boundaries, specify filters, and query the PASTA database programmatically:

```python
import shapely.geometry
from state_filter import load_state_geometry, search_and_filter_all

# 1. Resolve target US State geometry (as a Shapely Polygon or MultiPolygon)
state_geom = load_state_geometry("South Carolina")

# 2. Define semantic filters (keys accept single strings or lists of strings)
filters = {
    "keyword": ["sediment", "estuary"],
    "organization": "NIN-LTER"
}

# 3. Query PASTA API in a paginated loop and filter spatially
package_ids = search_and_filter_all(
    state_name="South Carolina",
    semantic_options=filters,
    state_geometry=state_geom,
    mode="intersects"  # "within" checks strict full containment, "intersects" includes border-crossing boxes
)

# 4. Consume matching package IDs
for pkg_id in package_ids:
    print(f"Matched package: {pkg_id}")
```

---

## 🛠️ Advantages of Programmatic Integration

1. **Robust Type Hinting:**
   Strict PEP 484 type annotations on all signatures provide comprehensive auto-completion, linting, and structural verification inside PyCharm, VS Code, and other IDEs.
2. **Self-Contained Spatial Resolving:**
   The package contains its own lightweight, offline coordinates data bundle. No geographic API requests are made to resolve US State shapes or bounding boxes.
3. **Built-in XML Security:**
   Standard `defusedxml.ElementTree` parsing is handled transparently inside the package, protecting your hosting infrastructure from XXE (XML External Entity Injection) and Billion Laughs vulnerability vectors automatically.
