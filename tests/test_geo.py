"""Unit tests for geospatial loading and coordinate validation utilities."""

import pytest
from shapely.geometry.base import BaseGeometry
from state_filter.geo import load_state_geometry, load_state_bbox, validate_coordinates


def test_load_state_geometry_valid() -> None:
    """Verifies valid state shapes load correctly as Shapely geometries."""
    # Test South Carolina
    sc_geom = load_state_geometry("South Carolina")
    assert isinstance(sc_geom, BaseGeometry)
    assert sc_geom.is_valid

    # Test case insensitivity
    alaska_geom = load_state_geometry("aLaSkA")
    assert isinstance(alaska_geom, BaseGeometry)
    assert alaska_geom.is_valid


def test_load_state_geometry_invalid() -> None:
    """Verifies that an error is raised for non-existent states."""
    with pytest.raises(ValueError, match="not found in US states database"):
        load_state_geometry("Atlantis")


def test_load_state_bbox_valid() -> None:
    """Verifies state bounding boxes are loaded correctly."""
    bbox = load_state_bbox("South Carolina")
    assert "minLon" in bbox
    assert "maxLon" in bbox
    assert "minLat" in bbox
    assert "maxLat" in bbox

    assert bbox["minLon"] < bbox["maxLon"]
    assert bbox["minLat"] < bbox["maxLat"]

    # Test case insensitivity
    bbox_lower = load_state_bbox("south carolina")
    assert bbox == bbox_lower


def test_load_state_bbox_invalid() -> None:
    """Verifies that an error is raised for non-existent state bounding boxes."""
    with pytest.raises(ValueError, match="not found in bounding boxes database"):
        load_state_bbox("Atlantis")


@pytest.mark.parametrize(
    "lon, lat, expected",
    [
        (0.0, 0.0, True),
        (-180.0, -90.0, True),
        (180.0, 90.0, True),
        (-180.1, 0.0, False),
        (180.1, 0.0, False),
        (0.0, -90.1, False),
        (0.0, 90.1, False),
    ],
)
def test_validate_coordinates(lon: float, lat: float, expected: bool) -> None:
    """Tests coordinate validation edge cases."""
    assert validate_coordinates(lon, lat) == expected
