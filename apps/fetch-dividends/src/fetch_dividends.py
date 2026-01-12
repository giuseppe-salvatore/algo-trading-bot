#!/usr/bin/env python3
"""
Fetch dividend activities from Alpaca API.

Fetches dividend activities from Alpaca's API and saves them to
timestamped daily folders.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    from alpaca_api import AlpacaClient, load_config
except ImportError:
    # Fallback: add src directory to path and import modules directly
    project_root = Path(__file__).parent.parent.parent.parent
    src_path = project_root / "packages" / "alpaca-api" / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from alpaca_api import AlpacaClient, load_config


def get_output_directory(base_path: Path, date_str: str) -> Path:
    """
    Get the output directory for the given date.

    Args:
        base_path: Base output directory (e.g., data/dividends/alpaca/live)
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Path to the output directory
    """
    return base_path / date_str


def main():
    """Main entry point for fetch_dividends script."""
    parser = argparse.ArgumentParser(
        description="Fetch dividend activities from Alpaca API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all dividend activities (saves to today's date folder)
  fetch-dividends

  # Fetch dividends for a specific date range
  fetch-dividends --after 2024-01-01 --until 2024-12-31

  # Use custom output directory (for testing)
  fetch-dividends --output-dir data/dividends/alpaca/test
        """,
    )
    parser.add_argument(
        "--after",
        type=str,
        help="Fetch dividends after this date (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--until",
        type=str,
        help="Fetch dividends until this date (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Base output directory (default: data/dividends/alpaca/live)",
    )

    args = parser.parse_args()

    # Get project root (4 levels up from this file: src -> fetch-dividends -> apps -> root)
    project_root = Path(__file__).parent.parent.parent.parent

    # Determine output directory
    if args.output_dir:
        base_output_dir = Path(args.output_dir)
    else:
        base_output_dir = project_root / "data" / "dividends" / "alpaca" / "live"

    # Get today's date for folder name
    today = date.today()
    date_str = today.strftime("%Y-%m-%d")
    output_dir = get_output_directory(base_output_dir, date_str)

    print(f"Output directory: {output_dir}", file=sys.stderr)
    print("", file=sys.stderr)

    # Load configuration
    try:
        config_file = project_root / "config" / "alpaca-api.json"
        config = load_config(config_file)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    if not config.get("api_key") or not config.get("api_secret"):
        print(
            "Error: API key and secret are required. "
            "Set them in config/alpaca-api.json or via environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize client
    try:
        client = AlpacaClient(
            api_key=config["api_key"],
            api_secret=config["api_secret"],
            base_url=config.get("base_url", "https://api.alpaca.markets"),
        )
    except Exception as e:
        print(f"Error initializing Alpaca client: {e}", file=sys.stderr)
        sys.exit(1)

    # Fetch and save dividends
    try:
        print("Fetching dividend activities...", file=sys.stderr)
        if args.after:
            print(f"  After: {args.after}", file=sys.stderr)
        if args.until:
            print(f"  Until: {args.until}", file=sys.stderr)

        dividends = client.get_dividends(after=args.after, until=args.until)

        print(f"  Fetched {len(dividends)} dividend activities", file=sys.stderr)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write to file
        output_file = output_dir / "dividends.json"
        with open(output_file, "w") as f:
            json.dump(dividends, f, indent=2)

        print(f"  Written to {output_file}", file=sys.stderr)
        print("", file=sys.stderr)

        print("Summary:", file=sys.stderr)
        print(f"  Total dividends fetched: {len(dividends)}", file=sys.stderr)
        print(f"  Output directory: {output_dir}", file=sys.stderr)
        print("  File created: dividends.json", file=sys.stderr)

    except Exception as e:
        print(f"Error fetching dividends: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
