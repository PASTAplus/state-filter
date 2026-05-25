"""State Filter: Filter PASTA content by US geographic state boundaries.

This package provides a CLI and programming interface to search data packages
from the Environmental Data Initiative (EDI) and filter them using US State
spatial boundaries and semantic metadata.
"""

__version__ = "0.1.0"

from state_filter.geo import load_state_geometry, load_state_bbox, validate_coordinates
from state_filter.pasta import (
    build_solr_query,
    search_pasta,
    parse_and_filter_results,
    search_and_filter_all,
)

__all__ = [
    "load_state_geometry",
    "load_state_bbox",
    "validate_coordinates",
    "build_solr_query",
    "search_pasta",
    "parse_and_filter_results",
    "search_and_filter_all",
]
