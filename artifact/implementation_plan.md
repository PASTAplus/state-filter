# Implementation Plan - Project State-Filter

A command line application to discover and filter EDI PASTA data packages by US State using Solr spatial search and high-precision Shapely polygon boundaries.

## User Review Required

> [!IMPORTANT]
> **Key Decisions Adopted:**
> 1. **US State Polygons:** Offline, bundled lightweight GeoJSON file containing US state boundaries (including multipolygons for islands/borders).
> 2. **Solr Bounding Boxes:** Pre-computed and saved to a JSON file `bounding_boxes.json` mapping each state to `{"minLon": ..., "maxLon": ..., "maxLat": ..., "minLat": ...}` coordinates in key-value form to prevent coordinate-ordering mistakes.
> 3. **CLI Design:**
>    - Uses `click`.
>    - Allows multiple values for semantic options (e.g., `--keyword sediment --keyword sand`).
>    - Supports `--options-file <path>` in JSON format to load complex/long lists of options.
>    - `--mode` options are `within` (default) and `intersects`.
> 4. **XML Security:** Uses standard `defusedxml.ElementTree` to securely parse XML response payloads from PASTA.

---

## Proposed Changes

### Dependencies & Setup
We will update `pyproject.toml` to install:
* `click` (CLI library)
* `requests` (API requests)
* `shapely` (Geospatial calculations)
* `defusedxml` (Secure XML parsing)

#### [MODIFY] [pyproject.toml](file:///home/servilla/git/state-filter/pyproject.toml)
* Add dependencies: `click`, `requests`, `shapely`, `defusedxml`.
* Define CLI entry point: `state-filter = "state_filter.cli:main"`.
* Configure Pixi tasks for running tests and CLI verification.

---

### Data Assets

#### [NEW] [us_states.geojson](file:///home/servilla/git/state-filter/src/state_filter/data/us_states.geojson)
* A bundled, lightweight, simplified GeoJSON file containing coordinates and properties of all US States (including multipolygons for Alaska, Hawaii, etc.). We will fetch or compile a highly optimized/simplified version.

#### [NEW] [bounding_boxes.json](file:///home/servilla/git/state-filter/src/state_filter/data/bounding_boxes.json)
* Generated JSON map of state names to their exact bounding boxes (`minLon`, `maxLon`, `maxLat`, `minLat`).
* We will write a small helper utility `/home/servilla/git/state-filter/scratch/prepare_data.py` to extract these bounding boxes directly from `us_states.geojson` and save them.

---

### Source Code

#### [MODIFY] [__init__.py](file:///home/servilla/git/state-filter/src/state_filter/__init__.py)
* Expose key classes/functions if needed.

#### [NEW] [geo.py](file:///home/servilla/git/state-filter/src/state_filter/geo.py)
* `load_state_geometry(state_name: str) -> shapely.geometry.base.BaseGeometry`: Loads and merges state geometry from the bundled GeoJSON. Handles Multipolygons and Polygons.
* `load_state_bbox(state_name: str) -> dict[str, float]`: Loads pre-computed bounding box for a state from `bounding_boxes.json`.
* `validate_coordinates(lon: float, lat: float) -> bool`: Helper to ensure values are in standard ranges.

#### [NEW] [pasta.py](file:///home/servilla/git/state-filter/src/state_filter/pasta.py)
* `build_solr_query(state_name: str, semantic_options: dict) -> str`: Constructs the Solr query URL for PASTA search using `coordinates:IsWithin(West+East+North+South)` and other semantic query tokens.
* `search_pasta(query_url: str) -> str`: Executes the HTTP GET request to PASTA API and handles errors.
* `parse_and_filter_results(xml_content: str, state_geometry: shapely.geometry.base.BaseGeometry, mode: str) -> list[str]`:
  * Parses search XML securely using `defusedxml.ElementTree`.
  * Extracts each `<document>`'s `<packageid>` and `<coordinates>` (inside `<spatialCoverage>`).
  * Converts the coordinates string (e.g. `-79.2936 33.1925 -79.1042 33.357`) into a Shapely `box(minLon, minLat, maxLon, maxLat)`.
  * Performs high-precision filtering:
    * `within`: `state_geometry.contains(pkg_box)`
    * `intersects`: `state_geometry.intersects(pkg_box)`
  * Returns list of matching package identifiers (`packageid`).

#### [NEW] [cli.py](file:///home/servilla/git/state-filter/src/state_filter/cli.py)
* Click CLI command layout:
  ```python
  @click.command()
  @click.argument("state", type=str)
  @click.option("--organization", "-o", multiple=True, help="Filter by organization name.")
  @click.option("--geographic", "-g", multiple=True, help="Filter by geographic place name.")
  @click.option("--keyword", "-k", multiple=True, help="Filter by keyword.")
  @click.option("--abstract", "-a", multiple=True, help="Filter by abstract content.")
  @click.option("--options-file", "-f", type=click.Path(exists=True), help="Path to JSON file with additional options.")
  @click.option("--mode", "-m", type=click.Choice(["within", "intersects"]), default="within", show_default=True, help="Spatial filtering precision mode.")
  ```
* Combines command line parameters and option files (if provided).
* Calls the search and filtering logic in `pasta.py`.
* Outputs the resulting list of matching package identifiers to standard output (one per line).

---

## Verification Plan

### Automated Tests
We will add `pytest` unit and integration tests under `tests/`:
* **`tests/test_geo.py`**:
  * Verify `load_state_bbox` returns the correct coordinates.
  * Verify geometry containment and intersection queries for test coordinates using Shapely.
* **`tests/test_pasta.py`**:
  * Mock API responses to test `build_solr_query` URL generation with various combinations of CLI inputs.
  * Mock responses to test `parse_and_filter_results` with defusedxml, confirming strict `within` and `intersects` precision.
* **`tests/test_cli.py`**:
  * Use Click `CliRunner` to test CLI argument parsing, including options files and multi-value options.

### Manual Verification
* Execute CLI commands targeting different states (e.g. `"South Carolina"`, `"California"`) with single and multiple options.
* Provide an options JSON file and confirm it merges correctly with CLI arguments.
