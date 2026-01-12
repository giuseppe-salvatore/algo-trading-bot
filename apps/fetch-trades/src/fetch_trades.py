#!/usr/bin/env python3
"""
Fetch trading activities (FILL, NC, SPLIT) from Alpaca API.

Fetches trade fills, name changes, and stock splits from Alpaca's API
and saves them to timestamped daily folders.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    from alpaca_api import FILL, NC, SPLIT, AlpacaClient, load_config
except ImportError:
    # Fallback: add src directory to path and import modules directly
    project_root = Path(__file__).parent.parent.parent.parent
    src_path = project_root / "packages" / "alpaca-api" / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from alpaca_api import FILL, NC, SPLIT, AlpacaClient, load_config


def get_output_directory(base_path: Path, date_str: str) -> Path:
    """
    Get the output directory for the given date.

    Args:
        base_path: Base output directory (e.g., data/trading/alpaca/live)
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Path to the output directory
    """
    return base_path / date_str


def fetch_and_save_activities(
    client: AlpacaClient,
    activity_type: str,
    output_file: Path,
    after: str | None = None,
    until: str | None = None,
) -> int:
    """
    Fetch activities of a specific type and save to JSON file.

    Args:
        client: AlpacaClient instance
        activity_type: Activity type (FILL, NC, SPLIT)
        output_file: Path to output JSON file
        after: Fetch activities after this date (YYYY-MM-DD format)
        until: Fetch activities until this date (YYYY-MM-DD format)

    Returns:
        Number of activities fetched
    """
    activity_type_name = {
        FILL: "FILL",
        NC: "Name Changes",
        SPLIT: "Splits",
    }.get(activity_type, activity_type)

    print(f"Fetching {activity_type_name} activities...", file=sys.stderr)
    if after:
        print(f"  After: {after}", file=sys.stderr)
    if until:
        print(f"  Until: {until}", file=sys.stderr)

    try:
        if activity_type == FILL:
            activities = client.get_trade_fills(after=after, until=until)
        elif activity_type == NC:
            activities = client.get_name_changes(after=after, until=until)
        elif activity_type == SPLIT:
            activities = client.get_splits(after=after, until=until)
        else:
            activities = client.get_activities(activity_type, after=after, until=until)

        print(
            f"  Fetched {len(activities)} {activity_type_name.lower()} activities", file=sys.stderr
        )

        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(activities, f, indent=2)

        print(f"  Written to {output_file}", file=sys.stderr)
        return len(activities)

    except Exception as e:
        print(f"Error fetching {activity_type_name}: {e}", file=sys.stderr)
        raise


def main():
    """Main entry point for fetch_trades script."""
    parser = argparse.ArgumentParser(
        description="Fetch trading activities (FILL, NC, SPLIT) from Alpaca API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all trading activities (saves to today's date folder)
  fetch-trades

  # Fetch activities for a specific date range
  fetch-trades --after 2024-01-01 --until 2024-12-31

  # Use custom output directory (for testing)
  fetch-trades --output-dir data/trading/alpaca/test
        """,
    )
    parser.add_argument(
        "--after",
        type=str,
        help="Fetch activities after this date (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--until",
        type=str,
        help="Fetch activities until this date (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Base output directory (default: data/trading/alpaca/live)",
    )

    args = parser.parse_args()

    # Get project root (4 levels up from this file: src -> fetch-trades -> apps -> root)
    project_root = Path(__file__).parent.parent.parent.parent

    # Determine output directory
    if args.output_dir:
        base_output_dir = Path(args.output_dir)
    else:
        base_output_dir = project_root / "data" / "trading" / "alpaca" / "live"

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

    # Fetch and save activities
    total_activities = 0
    try:
        # Fetch FILL activities (trade fills)
        fills_file = output_dir / "taxable_activities.json"
        fills_count = fetch_and_save_activities(
            client, FILL, fills_file, after=args.after, until=args.until
        )
        total_activities += fills_count
        print("", file=sys.stderr)

        # Fetch NC activities (name changes)
        name_changes_file = output_dir / "name_changes.json"
        nc_count = fetch_and_save_activities(
            client, NC, name_changes_file, after=args.after, until=args.until
        )
        total_activities += nc_count
        print("", file=sys.stderr)

        # Fetch SPLIT activities (stock splits)
        splits_file = output_dir / "splits.json"
        splits_count = fetch_and_save_activities(
            client, SPLIT, splits_file, after=args.after, until=args.until
        )
        total_activities += splits_count
        print("", file=sys.stderr)

        print("Summary:", file=sys.stderr)
        print(f"  Total activities fetched: {total_activities}", file=sys.stderr)
        print(f"  Output directory: {output_dir}", file=sys.stderr)
        print("  Files created:", file=sys.stderr)
        print(f"    - taxable_activities.json ({fills_count} activities)", file=sys.stderr)
        print(f"    - name_changes.json ({nc_count} activities)", file=sys.stderr)
        print(f"    - splits.json ({splits_count} activities)", file=sys.stderr)

    except Exception as e:
        print(f"Error fetching activities: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
