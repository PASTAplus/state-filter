# Walkthrough - Project State-Filter Complete

We have completed the implementation of the `state-filter` command line application. It successfully retrieves and processes ecological data packages from the Environmental Data Initiative (EDI) repository based on US State boundaries and semantic metadata.

---

## 🛠️ Accomplished Tasks

### 1. Setup & Environment
* Configured `pyproject.toml` using Pixi for package management.
* Configured all Python dependencies (`click`, `requests`, `shapely`, `defusedxml`) to strictly resolve from Conda (`conda-forge`), ensuring binary safety for complex geometry libraries like Shapely.
* Created standard Pixi tasks for `test`, `lint`, and `format`.
* Defined the CLI entrypoint: `state-filter = "state_filter.cli:main"`.

### 2. Core Geospatial Integration (`state_filter/geo.py`)
* Embedded a lightweight, optimized GeoJSON containing coordinate descriptions of all US States (including multipolygons for Alaska, Hawaii, and complex coastlines).
* Implemented automatic topological repair using `shapely.validation.make_valid` to resolve self-intersecting segments in simplified boundaries (e.g. Alaska islands).
* Generated a pre-computed JSON lookup `bounding_boxes.json` mapping states to exact longitudinal/latitudinal ranges (`minLon`, `maxLon`, `maxLat`, `minLat`).

### 3. Solr WKT Spatial Querying & Secure Parsing (`state_filter/pasta.py`)
* Formatted spatial filters using Solr's strict WKT syntax: `coordinates:"IsWithin(ENVELOPE(minLon, maxLon, maxLat, minLat))"`.
* Implemented secure XML parsing using `defusedxml.ElementTree` to safeguard against XXE (XML External Entity) and entity expansion vulnerability vectors.
* Enabled parsing of returned coordinates represented in both raw space-separated format (`West South East North`) and Solr's native spatial `ENVELOPE(West, East, North, South)` structure.
* Performed high-precision geometry validation using Shapely checking:
  * `within` (Default): `state_geometry.contains(pkg_box)`
  * `intersects`: `state_geometry.intersects(pkg_box)`

### 4. Automatic Seamless Pagination (`state_filter/pasta.py` & `state_filter/cli.py`)
* Upgraded `build_solr_query` to accept configurable `start` and `rows` offsets.
* Designed a new API method `search_and_filter_all` implementing a robust pagination fetch loop. It extracts Solr pagination metadata (`numFound`, `start`, `rows`) directly from the `<resultset>` XML attributes, executing subsequent pages until all matching datasets have been fully resolved.
* Combined and deduplicated matching package IDs across all query pages seamlessly.
* Updated `cli.py` to route all queries through this paginated wrapper automatically.

### 5. API Key Parameter Routing
* Implemented support for appending an API key as a query parameter named `key` at the end of the PASTA URL.
* Exposed the CLI switch `--api-key` to pass the key parameter securely at runtime.
* Added matching JSON options file support to parse `"api_key"` or `"key"` parameters from structured configurations automatically.

### 6. Click CLI & Options File Merge (`state_filter/cli.py`)
* Created the primary Click command routing standard arguments (`STATE`) and options (`--keyword`, `--organization`, `--geographic`, `--abstract`).
* Enabled multi-value parameters (e.g. `--keyword sediment --keyword sand`).
* Supported a structured `--options-file <path>` in JSON format to merge complex nested configurations gracefully.

---

## 🧪 Verification & Quality Control

### 1. Pytest Suite
We implemented 23 distinct tests verifying every tier of the application under `tests/`:
* **`tests/test_geo.py`**: Asserts bounding boxes, boundary containment/intersections, and coordinates validation range limits.
* **`tests/test_pasta.py`**: Confirms correct Solr eDisMax query serialization, WKT encoding, secure parsing, and **verifies both paginated query offsets and api-key forwarding**.
* **`tests/test_cli.py`**: Uses Click `CliRunner` to check options parsing, file merging logic, standard output, and **verifies that --api-key arguments are correctly forwarded to the API**.

```bash
pixi run test
```
**Results:** `23 passed in 0.19s` (100% success).

### 2. Formatting & Linting
Enforced ruff linter and PEP 8 styling completely:
```bash
pixi run lint   # All checks passed!
pixi run format # Clean format enforcement on all files.
```

### 3. Manual Live Execution
```bash
# Querying South Carolina in intersects mode with dummy api-key parameter
pixi run state-filter "South Carolina" --keyword sediment --mode intersects --api-key "test_key_abc"
```
**Output:** `knb-lter-nin.8.1` (successfully matching the EDI database in real-time).
