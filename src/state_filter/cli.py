"""Command Line Interface for filtering EDI PASTA data packages by state.

This module provides the Click CLI definition, combining options files and
command-line arguments, invoking Solr queries, and outputting filtered results.
"""

import json
import sys
from typing import Any
import click
import requests

from state_filter.geo import load_state_geometry
from state_filter.pasta import search_and_filter_all


def merge_list_option(cli_vals: tuple[str, ...], file_val: Any) -> list[str]:
    """Helper to merge values from CLI argument list and option files.

    Args:
        cli_vals: Tuple of strings provided via CLI.
        file_val: Value provided in JSON options file (could be string or list).

    Returns:
        list[str]: A merged and deduplicated list of values.
    """
    merged = list(cli_vals)
    if isinstance(file_val, list):
        merged.extend(str(x) for x in file_val if x)
    elif file_val:
        merged.append(str(file_val))

    # Strip whitespace and deduplicate while maintaining order
    seen = set()
    cleaned = []
    for val in merged:
        v_stripped = val.strip()
        if v_stripped and v_stripped not in seen:
            seen.add(v_stripped)
            cleaned.append(v_stripped)

    return cleaned


@click.command()
@click.argument("state", type=str)
@click.option(
    "--organization",
    "-o",
    multiple=True,
    help="Filter by organization name. Can be specified multiple times.",
)
@click.option(
    "--geographic",
    "-g",
    multiple=True,
    help="Filter by geographic place name. Can be specified multiple times.",
)
@click.option(
    "--keyword",
    "-k",
    multiple=True,
    help="Filter by keyword. Can be specified multiple times.",
)
@click.option(
    "--abstract",
    "-a",
    multiple=True,
    help="Filter by abstract text. Can be specified multiple times.",
)
@click.option(
    "--options-file",
    "-f",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to JSON file containing structured query filter options.",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["within", "intersects"]),
    default="within",
    show_default=True,
    help="Spatial filtering mode (within US State geometry vs. intersecting).",
)
@click.option(
    "--api-key",
    help="Optional API key query parameter to append to PASTA REST API requests.",
)
@click.option(
    "--connector",
    "-c",
    type=click.Choice(["and", "or"]),
    help="Logical connector for combining semantic options. [default: or]",
)
def main(
    state: str,
    organization: tuple[str, ...],
    geographic: tuple[str, ...],
    keyword: tuple[str, ...],
    abstract: tuple[str, ...],
    options_file: str | None,
    mode: str,
    api_key: str | None = None,
    connector: str | None = None,
) -> None:
    """Filter EDI PASTA data packages by US State and semantic options.

    STATE is the name of the US State (e.g., "South Carolina", "Alaska").
    """
    options_data: dict[str, Any] = {}
    if options_file:
        try:
            with open(options_file, "r", encoding="utf-8") as f:
                options_data = json.load(f)
            if not isinstance(options_data, dict):
                click.echo(
                    f"Error: Options file '{options_file}' must contain a JSON object.",
                    err=True,
                )
                sys.exit(1)
        except json.JSONDecodeError as e:
            click.echo(
                f"Error parsing options file '{options_file}': {e}",
                err=True,
            )
            sys.exit(1)
        except OSError as e:
            click.echo(
                f"Error reading options file '{options_file}': {e}",
                err=True,
            )
            sys.exit(1)

    # Merge semantic filters
    semantic_options = {
        "abstract": merge_list_option(abstract, options_data.get("abstract")),
        "organization": merge_list_option(
            organization, options_data.get("organization")
        ),
        "keyword": merge_list_option(keyword, options_data.get("keyword")),
        "geographic": merge_list_option(geographic, options_data.get("geographic")),
    }

    # Resolve API key from CLI or options file
    resolved_api_key = api_key or options_data.get("api_key") or options_data.get("key")

    # Resolve logical connector from CLI or options file, defaulting to "or"
    resolved_connector = connector or options_data.get("connector") or "or"

    try:
        # 1. Resolve and validate target US State geometry using Shapely
        state_geometry = load_state_geometry(state)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(f"System Error: {e}", err=True)
        sys.exit(2)

    try:
        # Query PASTA REST API in a paginated loop and filter spatially
        matching_packages = search_and_filter_all(
            state,
            semantic_options,
            state_geometry,
            mode,
            api_key=resolved_api_key,
            connector=resolved_connector,
        )

        # 5. Output matching package IDs
        if matching_packages:
            for pkg_id in matching_packages:
                click.echo(pkg_id)
        else:
            # Output nothing on stdout as per CLI conventions when no records match
            pass

    except requests.RequestException as e:
        click.echo(f"Error communicating with PASTA REST API: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
