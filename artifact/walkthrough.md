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
* Formatted candidate spatial filters using Solr's WKT syntax dynamically based on the selected mode: `coordinates:"IsWithin(ENVELOPE(...))"` by default (for `"within"` mode) to strictly enclose coordinates, and `coordinates:"Intersects(ENVELOPE(...))"` (for `"intersects"` mode). Using `Intersects` when requested ensures that packages with multiple coordinate elements spread across different regions (e.g. some in California, some outside) are successfully retrieved as candidates by Solr and then filtered in-memory using Shapely.
* Implemented secure XML parsing using `defusedxml.ElementTree` to safeguard against XXE (XML External Entity) and entity expansion vulnerability vectors.
* Enabled parsing of returned coordinates represented in both raw space-separated format (`West South East North`) and Solr's native spatial `ENVELOPE(West, East, North, South)` structure.
* **Point & Degenerate Envelope Normalization:** Gracefully normalizes point-like bounding boxes (where min/max longitude and latitude are equal) into `shapely.geometry.Point` geometries and line-like bounding boxes into `shapely.geometry.LineString` geometries, avoiding topologically invalid degenerate polygons and ensuring 100% accurate spatial operations.
* Performed high-precision geometry validation using Shapely checking:
  * `within` (Default): `state_geometry.contains(pkg_box)`
  * `intersects`: `state_geometry.intersects(pkg_box)`

### 4. Automatic Seamless Pagination (`state_filter/pasta.py` & `state_filter/cli.py`)
* Upgraded `build_solr_query` to accept configurable `start` and `rows` offsets.
* Designed a new API method `search_and_filter_all` implementing a robust pagination fetch loop. It extracts Solr pagination metadata (`numFound`, `start`, `rows`) directly from the `<resultset>` XML attributes, executing subsequent pages until all matching datasets have been fully resolved.
* Combined and deduplicated matching package IDs across all query pages seamlessly.
* Updated `cli.py` to route all queries through this paginated wrapper automatically.

### 5. Configurable Semantic Connectors (AND / OR)
* Implemented a new option `--connector` / `-c` allowing users to determine the logical operator used to combine different semantic query terms (such as keywords, abstracts, organizations, and place names).
* **Logical OR by Default:** In accordance with the project requirements, different semantic criteria are combined using a logical **`OR`** by default (e.g. `q=keyword:"sediment" OR organization:"NIN-LTER"`).
* **Guaranteed Bounding Box AND-ing:** The spatial bounding box coordinates filter query (`fq=coordinates:IsWithin(...)`) is always combined as a logical **`AND`**, ensuring that spatial results are strictly intersected regardless of the semantic options configuration.
* Added support in options files to load the `"connector"` key programmatically.

### 6. API Key Parameter Routing
* Implemented support for appending an API key as a query parameter named `key` at the end of the PASTA URL.
* Exposed the CLI switch `--api-key` to pass the key parameter securely at runtime.
* Added matching JSON options file support to parse `"api_key"` or `"key"` parameters from structured configurations automatically.

### 7. Click CLI & Options File Merge (`state_filter/cli.py`)
* Created the primary Click command routing standard arguments (`STATE`) and options (`--keyword`, `--organization`, `--geographic`, `--abstract`, and `--title`).
* Enabled multi-value parameters (e.g. `--keyword sediment --keyword sand`, `--title greenhouse`).
* Supported a structured `--options-file <path>` in JSON format to merge complex nested configurations gracefully.

### 8. Multiple Coordinates Support (Logical ANY)
* Enhanced spatial extraction logic using `doc.findall(".//spatialCoverage/coordinates")` to support data packages returning multiple `<coordinates>` tags across one or more `<spatialCoverage>` sections.
* Implemented a logical **`ANY`** boundary matching system: if *any* coordinates satisfy the target containment/intersection boundary check, the package is included.
* Standardized coordinate extraction to handle malformed coordinates robustly without breaking package processing iteration.

---

## 🧪 Verification & Quality Control

### 1. Pytest Suite
We implemented 26 distinct tests verifying every tier of the application under `tests/`:
* **`tests/test_geo.py`**: Asserts bounding boxes, boundary containment/intersections, and coordinates validation range limits.
* **`tests/test_pasta.py`**: Confirms correct Solr eDisMax query serialization, WKT encoding, secure parsing, paginated query offsets, API key forwarding, custom logical connectors (AND/OR), logical ANY matching across multiple coordinates elements, and **graceful handling/normalizing of degenerate point/line envelopes**.
* **`tests/test_cli.py`**: Uses Click `CliRunner` to check options parsing, file merging logic, standard output, and verifies that `--api-key` and `--connector` arguments are correctly forwarded.

```bash
pixi run test
```
**Results:** `26 passed in 0.20s` (100% success).

### 2. Formatting & Linting
Enforced ruff linter and PEP 8 styling completely:
```bash
pixi run lint   # All checks passed!
pixi run format # Clean format enforcement on all files.
```

### 3. Manual Live Execution
```bash
# Querying South Carolina in intersects mode using logical AND to combine criteria
pixi run state-filter "South Carolina" --organization NIN-LTER --keyword dummy --mode intersects --connector and
# Output is empty (as expected because there are no packages with keyword "dummy")

# Querying South Carolina in intersects mode using logical OR to combine criteria (default)
pixi run state-filter "South Carolina" --organization NIN-LTER --keyword dummy --mode intersects --connector or
# Output: knb-lter-nin.8.1 (and 17 others matching organization "NIN-LTER")
```
