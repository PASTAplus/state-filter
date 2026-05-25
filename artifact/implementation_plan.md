# Implementation Plan - Project State-Filter

A command line application to discover and filter EDI PASTA data packages by US State using Solr spatial search and high-precision Shapely polygon boundaries.

## User Review Required

> [!IMPORTANT]
> **Key Decisions Adopted:**
> 1. **US State Polygons:** Offline, bundled lightweight GeoJSON file containing US state boundaries (including multipolygons for islands/borders).
> 2. **Solr Bounding Boxes:** Pre-computed and saved to a JSON file `bounding_boxes.json` mapping each state to `{"minLon": ..., "maxLon": ..., "maxLat": ..., "minLat": ...}` coordinates in key-value form to prevent coordinate-ordering mistakes.
> 3. **Configurable Logical Connectors (AND / OR):**
>    - Uses `--connector` / `-c` (choice `["and", "or"]`, defaulting to `"or"`) to combine semantic search terms.
>    - Bounding box spatial queries are **always** strictly intersected (logical `AND` via `fq` parameters), ensuring results are spatially correct regardless of semantic configuration.
> 4. **CLI Design:**
>    - Uses `click`.
>    - Allows multiple values for semantic options (e.g., `--keyword sediment --keyword sand`).
>    - Supports `--options-file <path>` in JSON format to load complex/long lists of options.
>    - `--mode` options are `within` (default) and `intersects`.
>    - Supports `--api-key` (forwarded as query parameter `key`).
> 5. **XML Security:** Uses standard `defusedxml.ElementTree` to securely parse XML response payloads from PASTA.

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
* `build_solr_query(state_name: str, semantic_options: dict, start: int = 0, rows: int = 1000, api_key: str | None = None, connector: str = "or") -> list[tuple[str, str]]`: Constructs the Solr query URL for PASTA search using WKT `coordinates:"IsWithin(ENVELOPE(minLon, maxLon, maxLat, minLat))"`, custom logical connector, and other parameters.
* `search_pasta(query_params: list[tuple[str, str]], timeout: int = 30) -> str`: Executes the HTTP GET request to PASTA API and handles errors.
* `parse_and_filter_results(xml_content: str, state_geometry: shapely.geometry.base.BaseGeometry, mode: str) -> list[str]`: Securely parses returned coordinates and filters by polygon boundaries.
* `search_and_filter_all(state_name: str, semantic_options: dict, state_geometry: BaseGeometry, mode: str, api_key: str | None = None, connector: str = "or") -> list[str]`: Implements the paginated loop to retrieve and filter all matches.

#### [NEW] [cli.py](file:///home/servilla/git/state-filter/src/state_filter/cli.py)
* Click CLI command layout:
  ```python
  @click.command()
  @click.argument("state", type=str)
  @click.option("--organization", "-o", multiple=True)
  @click.option("--geographic", "-g", multiple=True)
  @click.option("--keyword", "-k", multiple=True)
  @click.option("--abstract", "-a", multiple=True)
  @click.option("--options-file", "-f", type=click.Path(exists=True))
  @click.option("--mode", "-m", type=click.Choice(["within", "intersects"]), default="within")
  @click.option("--api-key")
  @click.option("--connector", "-c", type=click.Choice(["and", "or"]))
  ```
* Combines command line parameters and option files.
* Calls `search_and_filter_all` inside `pasta.py`.
* Outputs the resulting list of matching package identifiers to standard output (one per line).

---

## Verification Plan

### Automated Tests
We will add `pytest` unit and integration tests under `tests/`:
* **`tests/test_geo.py`**: Verify bounding box loading and coordinate range validation.
* **`tests/test_pasta.py`**: Verify Solr eDisMax query serialization, WKT coordinates, paginated loop mockups, and `AND` vs. `OR` logical connector combinations.
* **`tests/test_cli.py`**: Verify click CLI argument parsing, option file merges, `--api-key` routing, and `--connector` forwarding.

### Manual Verification
* Execute CLI commands with combinations of multiple options.
* Toggle `--connector and` and `--connector or` to verify query filtering behavior matches expectations.
