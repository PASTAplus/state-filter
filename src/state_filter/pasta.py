"""PASTA REST API query construction, execution, and secure XML filtering.

This module provides functions to search the Environmental Data Initiative (EDI)
PASTA repository, construct Solr query strings, securely parse returned XML,
and perform spatial containment/intersection checks against state boundaries.
"""

from typing import Any
import requests
import shapely.geometry
from shapely.geometry.base import BaseGeometry
import defusedxml.ElementTree as ET

from state_filter.geo import load_state_bbox, validate_coordinates

# Base URL for PASTA+ Data Package Manager Search
PASTA_SEARCH_URL = "https://pasta.lternet.edu/package/search/eml"


def build_solr_query(
    state_name: str,
    semantic_options: dict[str, Any],
    start: int = 0,
    rows: int = 1000,
    api_key: str | None = None,
    connector: str = "or",
    mode: str = "within",
) -> list[tuple[str, str]]:
    """Constructs the list of query parameters for the PASTA Solr search.

    The state_name is used to retrieve the pre-computed state bounding box,
    which is passed as a filter query (fq) using the IsWithin or Intersects spatial operator.
    Other optional semantic parameters are mapped to Solr metadata fields in the
    main query (q) parameter using Extended DisMax (eDisMax) syntax.

    Args:
        state_name: The name of the US State.
        semantic_options: Dictionary containing optional filters.
        start: Bounding box search pagination start offset.
        rows: Number of matching documents to retrieve per page.
        api_key: Optional API key.
        connector: Logical connector (and/or) for semantic options.
        mode: Spatial filtering mode ("within" or "intersects").

    Returns:
        list[tuple[str, str]]: List of query parameter tuples suitable for requests.
    """
    bbox = load_state_bbox(state_name)

    # Format the spatial query using standard WKT ENVELOPE syntax
    # expected by Solr/PASTA: coordinates:"IsWithin(ENVELOPE(...))" or "Intersects(ENVELOPE(...))"
    operator = "IsWithin" if mode == "within" else "Intersects"
    spatial_fq = (
        f'coordinates:"{operator}(ENVELOPE({bbox["minLon"]}, {bbox["maxLon"]}, '
        f'{bbox["maxLat"]}, {bbox["minLat"]}))"'
    )

    # Map semantic options to Solr schema fields
    field_mappings = {
        "abstract": "abstract",
        "organization": "organization",
        "keyword": "keyword",
        "geographic": "geographicdescription",
        "title": "title",
        "author": "author",
    }

    q_parts = []
    for opt_key, solr_field in field_mappings.items():
        val = semantic_options.get(opt_key)
        if not val:
            continue

        # Normalize to list of strings
        if isinstance(val, str):
            vals = [val]
        elif isinstance(val, (list, tuple)):
            vals = [str(v) for v in val if v]
        else:
            continue

        if not vals:
            continue

        # Format values safely with quotes to handle spaces correctly
        quoted_vals = []
        for v in vals:
            # Strip any surrounding quotes to avoid double-quoting
            v_clean = v.strip().strip('"').strip("'")
            quoted_vals.append(f'"{v_clean}"')

        if len(quoted_vals) == 1:
            q_parts.append(f"{solr_field}:{quoted_vals[0]}")
        else:
            joined_vals = " OR ".join(quoted_vals)
            q_parts.append(f"{solr_field}:({joined_vals})")

    # Combine field clauses using the specified connector (AND / OR)
    connector_str = f" {connector.strip().upper()} "
    q_str = connector_str.join(q_parts) if q_parts else "*:*"

    # Construct the final list of query parameters
    params = [
        ("defType", "edismax"),
        ("q", q_str),
        ("fq", spatial_fq),
        ("fq", "-scope:ecotrends"),
        ("fq", "-scope:lter-landsat*"),
        ("fl", "*"),
        ("sort", "score,desc,packageid,asc"),
        ("start", str(start)),
        ("rows", str(rows)),
    ]

    if api_key:
        params.append(("key", api_key))

    return params


def search_pasta(query_params: list[tuple[str, str]], timeout: int = 30) -> str:
    """Executes a Solr search request to the PASTA REST API.

    Args:
        query_params: The query parameters tuples list.
        timeout: Request timeout in seconds.

    Returns:
        str: Raw XML response payload.

    Raises:
        requests.RequestException: If the HTTP request fails.
    """
    response = requests.get(PASTA_SEARCH_URL, params=query_params, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_and_filter_results(
    xml_content: str, state_geometry: BaseGeometry, mode: str
) -> list[str]:
    """Securely parses the search XML and filters data packages by high-precision boundaries.

    Args:
        xml_content: Raw XML string response from PASTA.
        state_geometry: Shapely geometry (Polygon/MultiPolygon) of the target US state.
        mode: Filtering precision mode. Either "within" or "intersects".

    Returns:
        list[str]: A list of matching unique package ID strings (packageid).
    """
    if not xml_content.strip():
        return []

    # defusedxml wrapper prevents XXE/Entity Expansion attacks securely
    root = ET.fromstring(xml_content)
    matching_packages = []

    for doc in root.findall(".//document"):
        pkg_id_elem = doc.find("packageid")
        if pkg_id_elem is None or not pkg_id_elem.text:
            continue
        packageid = pkg_id_elem.text.strip()

        # Extract all coordinate elements under spatialCoverage
        coord_elems = doc.findall(".//spatialCoverage/coordinates")
        if not coord_elems:
            continue

        any_matched = False
        for coord_elem in coord_elems:
            if not coord_elem.text:
                continue

            coords_str = coord_elem.text.strip()
            import re

            # Extract all floats/ints from the coordinates string (supporting ENVELOPE format)
            nums = [
                float(x) for x in re.findall(r"[-+]?\d*\.\d+|\b[-+]?\d+\b", coords_str)
            ]
            if not nums:
                continue

            pkg_geom = None

            if coords_str.upper().startswith("ENVELOPE"):
                if len(nums) == 4:
                    # ENVELOPE(West, East, North, South) -> minLon, maxLon, maxLat, minLat
                    min_lon, max_lon, max_lat, min_lat = nums

                    # Validate coordinates range
                    if not (
                        validate_coordinates(min_lon, min_lat)
                        and validate_coordinates(max_lon, max_lat)
                    ):
                        continue

                    # Handle degenerate coordinate bounds (points or lines) elegantly
                    if min_lon == max_lon and min_lat == max_lat:
                        pkg_geom = shapely.geometry.Point(min_lon, min_lat)
                    elif min_lon == max_lon or min_lat == max_lat:
                        pkg_geom = shapely.geometry.LineString(
                            [(min_lon, min_lat), (max_lon, max_lat)]
                        )
                    else:
                        pkg_geom = shapely.geometry.box(
                            min_lon, min_lat, max_lon, max_lat
                        )
            else:
                if len(nums) == 4:
                    # West South East North -> minLon, minLat, maxLon, maxLat
                    min_lon, min_lat, max_lon, max_lat = nums

                    # Validate coordinates range
                    if not (
                        validate_coordinates(min_lon, min_lat)
                        and validate_coordinates(max_lon, max_lat)
                    ):
                        continue

                    # Handle degenerate coordinate bounds (points or lines) elegantly
                    if min_lon == max_lon and min_lat == max_lat:
                        pkg_geom = shapely.geometry.Point(min_lon, min_lat)
                    elif min_lon == max_lon or min_lat == max_lat:
                        pkg_geom = shapely.geometry.LineString(
                            [(min_lon, min_lat), (max_lon, max_lat)]
                        )
                    else:
                        pkg_geom = shapely.geometry.box(
                            min_lon, min_lat, max_lon, max_lat
                        )

                elif len(nums) == 2:
                    # Point representation: Longitude Latitude
                    lon, lat = nums
                    if not validate_coordinates(lon, lat):
                        continue
                    pkg_geom = shapely.geometry.Point(lon, lat)

            if pkg_geom is None:
                continue

            # Apply high-precision filtering using Shapely
            if mode == "within":
                if state_geometry.contains(pkg_geom):
                    any_matched = True
                    break
            elif mode == "intersects":
                if state_geometry.intersects(pkg_geom):
                    any_matched = True
                    break

        if any_matched:
            matching_packages.append(packageid)

    return matching_packages


def search_and_filter_all(
    state_name: str,
    semantic_options: dict[str, Any],
    state_geometry: BaseGeometry,
    mode: str,
    timeout: int = 30,
    api_key: str | None = None,
    connector: str = "or",
) -> list[str]:
    """Queries PASTA REST API in a paginated loop and filters all results.

    Args:
        state_name: The name of the US State.
        semantic_options: Dictionary containing optional filters.
        state_geometry: Shapely geometry representing the target US State.
        mode: Filtering precision mode. Either "within" or "intersects".
        timeout: HTTP request timeout in seconds.
        api_key: Optional API key query parameter to append to PASTA REST API requests.
        connector: Optional logical connector to combine semantic options (AND/OR).

    Returns:
        list[str]: Aggregated list of all matching unique package IDs.
    """
    all_matching_packages = []
    start = 0
    rows = 1000

    while True:
        query_params = build_solr_query(
            state_name,
            semantic_options,
            start=start,
            rows=rows,
            api_key=api_key,
            connector=connector,
            mode=mode,
        )
        xml_response = search_pasta(query_params, timeout=timeout)

        if not xml_response.strip():
            break

        # Filter and retrieve matches from the current page
        page_matches = parse_and_filter_results(xml_response, state_geometry, mode)
        all_matching_packages.extend(page_matches)

        # Extract pagination metadata securely
        root = ET.fromstring(xml_response)
        num_found = int(root.attrib.get("numFound", 0))
        returned_start = int(root.attrib.get("start", 0))
        returned_rows = int(root.attrib.get("rows", 0))

        # Check if we have processed all pages or if the page size is 0
        if returned_rows == 0 or returned_start + returned_rows >= num_found:
            break

        # Move to next page offset
        start = returned_start + returned_rows

    # Deduplicate results while preserving order
    seen = set()
    deduped = []
    for pkg_id in all_matching_packages:
        if pkg_id not in seen:
            seen.add(pkg_id)
            deduped.append(pkg_id)

    return deduped
