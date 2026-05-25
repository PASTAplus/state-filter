"""Unit tests for PASTA REST API query construction and XML result parsing."""

from unittest.mock import patch
from typing import Any
import shapely.geometry
from state_filter.pasta import (
    build_solr_query,
    parse_and_filter_results,
    search_and_filter_all,
)


def test_build_solr_query_default() -> None:
    """Tests build_solr_query when only state is provided (no semantic filters)."""
    params = build_solr_query("South Carolina", {})
    params_dict = dict(params)

    # Required structure
    assert params_dict["defType"] == "edismax"
    assert params_dict["q"] == "*:*"
    assert params_dict["fl"] == "*"
    assert params_dict["sort"] == "score,desc,packageid,asc"
    assert params_dict["start"] == "0"
    assert params_dict["rows"] == "1000"

    # Verify fq list contains the state filter query and default exclusions
    fq_values = [v for k, v in params if k == "fq"]
    assert len(fq_values) == 3
    assert fq_values[0].startswith('coordinates:"IsWithin')
    assert "-scope:ecotrends" in fq_values
    assert "-scope:lter-landsat*" in fq_values


def test_build_solr_query_semantic() -> None:
    """Tests build_solr_query with single and multi-value semantic filters."""
    semantic_opts = {
        "abstract": "Vernberg",
        "organization": ["NIN-LTER", "LTER"],
        "keyword": ["sediment", "sand"],
        "geographic": "North Inlet",
    }

    params = build_solr_query("South Carolina", semantic_opts)
    params_dict = dict(params)

    q_val = params_dict["q"]
    # Check that each field query contains correct field and values
    assert 'abstract:"Vernberg"' in q_val
    assert 'organization:("NIN-LTER" OR "LTER")' in q_val
    assert 'keyword:("sediment" OR "sand")' in q_val
    assert 'geographicdescription:"North Inlet"' in q_val
    assert " OR " in q_val

    # Test explicit "and" connector
    params_and = build_solr_query("South Carolina", semantic_opts, connector="and")
    q_val_and = dict(params_and)["q"]
    assert " AND " in q_val_and


def test_build_solr_query_api_key() -> None:
    """Tests build_solr_query when api_key is supplied."""
    params = build_solr_query("South Carolina", {}, api_key="secret123")
    params_dict = dict(params)
    assert params_dict["key"] == "secret123"


def test_parse_and_filter_results_within() -> None:
    """Verifies that parse_and_filter_results matches within states correctly."""
    # A simplified state polygon representing a 10x10 square: Lon [0, 10], Lat [0, 10]
    state_geom = shapely.geometry.box(0, 0, 10, 10)

    # XML mock response
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <resultset numFound="3" start="0" rows="10">
        <document>
            <packageid>pkg.inside.1</packageid>
            <spatialCoverage>
                <coordinates>2 2 8 8</coordinates>
            </spatialCoverage>
        </document>
        <document>
            <packageid>pkg.outside.2</packageid>
            <spatialCoverage>
                <coordinates>8 8 12 12</coordinates>
            </spatialCoverage>
        </document>
        <document>
            <packageid>pkg.point.3</packageid>
            <spatialCoverage>
                <coordinates>5 5</coordinates>
            </spatialCoverage>
        </document>
    </resultset>
    """

    # Filter with within mode
    results = parse_and_filter_results(xml_content, state_geom, "within")

    # Within should return pkg.inside.1 and pkg.point.3 (both completely inside)
    assert "pkg.inside.1" in results
    assert "pkg.point.3" in results
    assert "pkg.outside.2" not in results  # Crossing boundary is excluded from within


def test_parse_and_filter_results_intersects() -> None:
    """Verifies that parse_and_filter_results matches intersecting packages."""
    # A simplified state polygon representing a 10x10 square: Lon [0, 10], Lat [0, 10]
    state_geom = shapely.geometry.box(0, 0, 10, 10)

    # XML mock response
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <resultset numFound="3" start="0" rows="10">
        <document>
            <packageid>pkg.inside.1</packageid>
            <spatialCoverage>
                <coordinates>2 2 8 8</coordinates>
            </spatialCoverage>
        </document>
        <document>
            <packageid>pkg.outside.2</packageid>
            <spatialCoverage>
                <coordinates>8 8 12 12</coordinates>
            </spatialCoverage>
        </document>
        <document>
            <packageid>pkg.completely.outside.3</packageid>
            <spatialCoverage>
                <coordinates>12 12 15 15</coordinates>
            </spatialCoverage>
        </document>
    </resultset>
    """

    # Filter with intersects mode
    results = parse_and_filter_results(xml_content, state_geom, "intersects")

    # Intersects should return inside and crossing, but not completely outside
    assert "pkg.inside.1" in results
    assert "pkg.outside.2" in results
    assert "pkg.completely.outside.3" not in results


def test_parse_and_filter_results_malformed() -> None:
    """Verifies malformed XML or coordinate definitions are skipped gracefully."""
    state_geom = shapely.geometry.box(0, 0, 10, 10)

    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <resultset numFound="2" start="0" rows="10">
        <document>
            <packageid>pkg.malformed.coords</packageid>
            <spatialCoverage>
                <coordinates>not-a-number 5 5 5</coordinates>
            </spatialCoverage>
        </document>
        <document>
            <packageid>pkg.bad.count</packageid>
            <spatialCoverage>
                <coordinates>1 2 3</coordinates>
            </spatialCoverage>
        </document>
        <document>
            <packageid>pkg.invalid.range</packageid>
            <spatialCoverage>
                <coordinates>200 5 210 10</coordinates>
            </spatialCoverage>
        </document>
    </resultset>
    """
    results = parse_and_filter_results(xml_content, state_geom, "within")
    assert len(results) == 0


@patch("state_filter.pasta.search_pasta")
def test_search_and_filter_all_paginated(mock_search: Any) -> None:
    """Tests search_and_filter_all to verify it loops paginated queries correctly."""
    state_geom = shapely.geometry.box(0, 0, 10, 10)

    # Page 1 mock response
    xml_page1 = """<?xml version="1.0" encoding="utf-8"?>
    <resultset numFound="3" start="0" rows="2">
        <document>
            <packageid>pkg.page1.1</packageid>
            <spatialCoverage>
                <coordinates>2 2 8 8</coordinates>
            </spatialCoverage>
        </document>
        <document>
            <packageid>pkg.page1.2</packageid>
            <spatialCoverage>
                <coordinates>2 2 8 8</coordinates>
            </spatialCoverage>
        </document>
    </resultset>
    """

    # Page 2 mock response
    xml_page2 = """<?xml version="1.0" encoding="utf-8"?>
    <resultset numFound="3" start="2" rows="2">
        <document>
            <packageid>pkg.page2.3</packageid>
            <spatialCoverage>
                <coordinates>2 2 8 8</coordinates>
            </spatialCoverage>
        </document>
    </resultset>
    """

    mock_search.side_effect = [xml_page1, xml_page2]

    # Run paginated filter
    results = search_and_filter_all("South Carolina", {}, state_geom, "within")

    # Should successfully aggregate packages across all pages
    assert results == ["pkg.page1.1", "pkg.page1.2", "pkg.page2.3"]

    # Verify search was called twice with correct start parameters
    assert mock_search.call_count == 2

    first_call_args = mock_search.call_args_list[0][0][0]
    second_call_args = mock_search.call_args_list[1][0][0]

    assert ("start", "0") in first_call_args
    assert ("start", "2") in second_call_args
