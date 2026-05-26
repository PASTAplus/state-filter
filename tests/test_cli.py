"""Unit and integration tests for CLI interaction and Click command handling."""

import json
from unittest.mock import patch
from typing import Any
from click.testing import CliRunner

from state_filter.cli import main, merge_list_option


def test_merge_list_option() -> None:
    """Verifies merge_list_option correctly combines, strips, and deduplicates input."""
    # List combinations
    merged = merge_list_option(("a", " b "), ["b", "c", ""])
    assert merged == ["a", "b", "c"]

    # Single value combination
    merged_single = merge_list_option(("a",), "d")
    assert merged_single == ["a", "d"]

    # Empty inputs
    assert merge_list_option((), None) == []


@patch("state_filter.cli.search_and_filter_all")
def test_cli_success(mock_search_filter: Any) -> None:
    """Tests typical successful CLI invocation and parsing."""
    mock_search_filter.return_value = ["knb-lter-nin.8.1"]

    runner = CliRunner()
    result = runner.invoke(main, ["South Carolina"])

    assert result.exit_code == 0
    assert "knb-lter-nin.8.1" in result.output


@patch("state_filter.cli.search_and_filter_all")
def test_cli_options_file_merging(mock_search_filter: Any) -> None:
    """Tests loading and merging parameters from an options file."""
    mock_search_filter.return_value = []

    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create temp JSON options file
        options = {
            "organization": ["NIN-LTER"],
            "keyword": ["sediment", "sand"],
            "title": ["EDI"],
            "author": ["Raymond"],
        }
        with open("options.json", "w", encoding="utf-8") as f:
            json.dump(options, f)

        # Run CLI with options file and direct arguments
        result = runner.invoke(
            main,
            [
                "South Carolina",
                "--keyword",
                "mud",
                "--title",
                "greenhouse",
                "--author",
                "Stanley",
                "--options-file",
                "options.json",
            ],
        )

        assert result.exit_code == 0
        # Verify passed parameters contain merged options:
        call_args = mock_search_filter.call_args[0][1]
        assert "mud" in call_args["keyword"]
        assert "sediment" in call_args["keyword"]
        assert "sand" in call_args["keyword"]
        assert "NIN-LTER" in call_args["organization"]
        assert "greenhouse" in call_args["title"]
        assert "EDI" in call_args["title"]
        assert "Stanley" in call_args["author"]
        assert "Raymond" in call_args["author"]


@patch("state_filter.cli.search_and_filter_all")
def test_cli_api_key_forwarding(mock_search_filter: Any) -> None:
    """Verifies that the --api-key argument is correctly forwarded."""
    mock_search_filter.return_value = []

    runner = CliRunner()
    result = runner.invoke(main, ["South Carolina", "--api-key", "secret123"])

    assert result.exit_code == 0
    # Verify api_key kwargs passed to search_and_filter_all
    call_kwargs = mock_search_filter.call_args[1]
    assert call_kwargs["api_key"] == "secret123"


@patch("state_filter.cli.search_and_filter_all")
def test_cli_connector_forwarding(mock_search_filter: Any) -> None:
    """Verifies that the --connector argument is correctly forwarded."""
    mock_search_filter.return_value = []

    runner = CliRunner()
    result = runner.invoke(main, ["South Carolina", "--connector", "and"])

    assert result.exit_code == 0
    # Verify connector kwargs passed to search_and_filter_all
    call_kwargs = mock_search_filter.call_args[1]
    assert call_kwargs["connector"] == "and"


def test_cli_invalid_state() -> None:
    """Verifies that the CLI returns failure on invalid state input."""
    runner = CliRunner()
    result = runner.invoke(main, ["Atlantis"])
    assert result.exit_code == 1
    assert "Error: State 'Atlantis' not found" in result.output
