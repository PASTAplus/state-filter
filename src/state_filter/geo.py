"""Geospatial utilities for US state shapes and coordinate validation.

This module provides functions to load bundled GeoJSON state geometries,
pre-computed Solr bounding boxes, and validate geographic coordinates.
"""

import json
import os
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

# Absolute path to directory containing bundled resources
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_state_geometry(state_name: str) -> BaseGeometry:
    """Loads and returns the Shapely geometry for a given US State.

    This function reads the bundled US states GeoJSON file, searches for the
    feature matching the provided state name (case-insensitive), and converts
    it into a Shapely geometry object (Polygon or MultiPolygon).

    Args:
        state_name: The name of the US State (e.g., "South Carolina").

    Returns:
        BaseGeometry: The Shapely Polygon or MultiPolygon geometry representing the state.

    Raises:
        ValueError: If the state_name is not found in the GeoJSON dataset.
        FileNotFoundError: If the bundled GeoJSON file is missing.
    """
    geojson_path = os.path.join(_DATA_DIR, "us_states.geojson")
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(f"Bundled GeoJSON file missing at {geojson_path}")

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    matching_geoms = []
    normalized_query = state_name.strip().lower()

    for feature in data.get("features", []):
        name = feature.get("properties", {}).get("name", "")
        if name.strip().lower() == normalized_query:
            geom = shape(feature["geometry"])
            if not geom.is_valid:
                from shapely.validation import make_valid

                geom = make_valid(geom)
            matching_geoms.append(geom)

    if not matching_geoms:
        raise ValueError(f"State '{state_name}' not found in US states database.")

    # In case a state is split across multiple features (e.g. multiple polygons), union them.
    if len(matching_geoms) == 1:
        return matching_geoms[0]
    else:
        from shapely.ops import unary_union

        return unary_union(matching_geoms)


def load_state_bbox(state_name: str) -> dict[str, float]:
    """Loads the pre-computed Solr bounding box for a given US State.

    Args:
        state_name: The name of the US State (e.g., "South Carolina").

    Returns:
        dict[str, float]: A dictionary containing "minLon", "maxLon", "maxLat",
            and "minLat" representing the bounding box.

    Raises:
        ValueError: If the state_name is not found in the pre-computed bounds.
        FileNotFoundError: If the bundled bounding boxes JSON file is missing.
    """
    bbox_path = os.path.join(_DATA_DIR, "bounding_boxes.json")
    if not os.path.exists(bbox_path):
        raise FileNotFoundError(f"Bundled bounding boxes file missing at {bbox_path}")

    with open(bbox_path, "r", encoding="utf-8") as f:
        bboxes = json.load(f)

    # Perform a case-insensitive lookup
    normalized_query = state_name.strip().lower()
    for name, bbox in bboxes.items():
        if name.strip().lower() == normalized_query:
            return bbox

    raise ValueError(f"State '{state_name}' not found in bounding boxes database.")


def validate_coordinates(lon: float, lat: float) -> bool:
    """Validates if a coordinate pair falls within standard geographic bounds.

    Args:
        lon: The longitude coordinate.
        lat: The latitude coordinate.

    Returns:
        bool: True if coordinates are within range, False otherwise.
    """
    return -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0
