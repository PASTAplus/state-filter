# State Filter

`state-filter` is a command line application and Python library designed to search ecological data packages from the Environmental Data Initiative (EDI) PASTA repository and filter them using high-precision US State geographic boundaries (including MultiPolygons for coastlines and islands) and semantic metadata.

---

## 🛠️ Features

* **High-Precision Spatial Filtering:** Parses metadata spatial coordinates and filters them against simplified offline US State polygon boundaries using `shapely` geometries.
* **Dual Spatial Precision Modes:**
  * `within` (Default): Matches data packages completely enclosed within the state boundary.
  * `intersects`: Matches data packages completely enclosed OR partially crossing the state border (essential for coastal/marine datasets).
* **Solr eDisMax Integration:** Translates geographic and semantic constraints into an optimized Apache Solr query leveraging strict WKT coordinate boundaries via the `IsWithin` spatial operator: `coordinates:"IsWithin(ENVELOPE(W, E, N, S))"`.
* **Configurable Semantic Connectors (AND / OR):** Allows combining semantic criteria (abstracts, keywords, organizations, place names) using either logical **`OR`** (Default) or logical **`AND`** operators, while **always** strictly intersecting the spatial bounding box filter query as a logical `AND`.
* **Automatic Pagination:** Automatically pages through query results recursively when matches exceed 1,000 documents, aggregating and deduplicating matches seamlessly.
* **Flexible CLI & Options File Merge:** Supports Click-based multi-value CLI parameters (e.g. `--keyword sediment --keyword sand`) and merges them gracefully with a structured JSON options file.
* **API Key Parameter Forwarding:** Supports the secure transmission of a `key` query parameter via the `--api-key` CLI option or structured option files.
* **Secure XML Processing:** Guards against XML External Entity (XXE) and XML Entity Expansion attacks using `defusedxml.ElementTree`.
* **Conda-First Dependency Safety:** Fully configured with `pixi` to resolve binary dependencies (like `shapely` and its underlying C-geospatial libraries) strictly from `conda-forge`.

---

## 🚀 Installation & Setup

Ensure you have [Pixi](https://pixi.sh) installed. Then, clone the repository and initialize the project:

```bash
# Clone the repository
git clone <repository_url> state-filter
cd state-filter

# Install all dependencies and initialize editable mode
pixi install
```

---

## 💻 CLI Usage Guide

The CLI accepts a required US State name as a positional argument, along with optional semantic filters and configurations.

```bash
Usage: state-filter [OPTIONS] STATE

  Filter EDI PASTA data packages by US State and semantic options.

  STATE is the name of the US State (e.g., "South Carolina", "Alaska").

Options:
  -m, --mode [within|intersects]  Spatial filtering mode (within US State
                                  geometry vs. intersecting).  [default:
                                  within]
  -o, --organization TEXT         Filter by organization name. Can be
                                  specified multiple times.
  -g, --geographic TEXT           Filter by geographic place name. Can be
                                  specified multiple times.
  -k, --keyword TEXT              Filter by keyword. Can be specified multiple
                                  times.
  -a, --abstract TEXT             Filter by abstract text. Can be specified
                                  multiple times.
  -f, --options-file FILE         Path to JSON file containing structured
                                  query filter options.
  -c, --connector [and|or]        Logical connector for combining semantic
                                  options. [default: or]
  --api-key TEXT                  Optional API key query parameter to append
                                  to PASTA REST API requests.
  -h, --help                      Show this message and exit.
```

### Examples

#### 1. Basic Spatial Search
Retrieve all packages whose metadata spatial footprint lies fully within South Carolina:
```bash
pixi run state-filter "South Carolina"
```

#### 2. Search by Keyword & Organization (Default OR Mode)
Retrieve packages matching either `"NIN-LTER"` organization **OR** `"dummy"` keyword (while strictly satisfying the South Carolina boundary intersection):
```bash
pixi run state-filter "South Carolina" --organization NIN-LTER --keyword dummy --mode intersects --connector or
```

#### 3. Search by Keyword & Organization (AND Mode)
Retrieve packages strictly matching both `"NIN-LTER"` organization **AND** `"dummy"` keyword (which yields empty as no datasets have `"dummy"` as a keyword):
```bash
pixi run state-filter "South Carolina" --organization NIN-LTER --keyword dummy --mode intersects --connector and
```

#### 4. Structured Filters via Options File & API Key
Load complex queries from a JSON options file (like the template in [docs/options_example.json](file:///home/servilla/git/state-filter/docs/options_example.json)) and supply a secure API key parameter:
```bash
pixi run state-filter "South Carolina" --options-file docs/options_example.json --api-key "your_secret_key"
```

---

## 📦 Programmatic Library Integration

`state-filter` is designed to be easily imported and used inside other Python applications. All public-facing modules are exposed directly at the package root level:

```python
import shapely.geometry
from state_filter import load_state_geometry, search_and_filter_all

# 1. Resolve target US State boundary polygon (repaired automatically)
state_geom = load_state_geometry("South Carolina")

# 2. Define semantic parameters
semantic_filters = {
    "keyword": ["sediment", "estuary"],
    "organization": "NIN-LTER"
}

# 3. Query API in a paginated loop and filter spatially
package_ids = search_and_filter_all(
    state_name="South Carolina",
    semantic_options=semantic_filters,
    state_geometry=state_geom,
    mode="intersects",
    api_key="your_secret_key",
    connector="or"  # optional, default is "or"
)

# 4. Consume matching package IDs
for pkg_id in package_ids:
    print(f"Matched package: {pkg_id}")
```

---

## 🧪 Verification & Development

We enforce high standards of code quality, formatting, and extensive test coverage using Pixi tasks.

### Running the Test Suite
We have constructed 24 automated tests covering geospatial parsing, Solr query serialization, custom logical connectors (AND/OR), pagination offsets, and CLI arguments.
```bash
pixi run test
```

### Linting & Code Quality Checks
Static analysis and PEP 8 imports/code rules are enforced via Ruff:
```bash
# Run Ruff linter checks
pixi run lint

# Auto-format all Python code
pixi run format
```
