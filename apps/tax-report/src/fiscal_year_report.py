#!/usr/bin/env python3
"""
Script to generate UK Financial Year capital gains reports across all symbols.
Processes all events from day 0 to maintain accurate cost basis, but only counts
profits from events within the specified UK FY period (April 6 to April 5).

Uses the same Average Cost Basis method as balance_tracker.py for consistency.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Import functions from balance_tracker and analyze_events
from analyze_events import analyze_events
from balance_tracker import (
    apply_splits,
    format_currency,
    load_name_changes,
    load_splits,
    resolve_symbol,
)


def parse_fy_date_range(fy_string: str) -> tuple[datetime, datetime]:
    """
    Parse UK Financial Year string and return date range.

    Args:
        fy_string: UK FY format "YYYY-YY" (e.g., "2025-26")

    Returns:
        Tuple of (start_date, end_date) where:
        - start_date: April 6, YYYY at 00:00:00
        - end_date: April 5, YYYY+1 at 23:59:59.999999

    Raises:
        ValueError: If fy_string format is invalid
    """
    # Parse format: "YYYY-YY" (e.g., "2025-26")
    if "-" not in fy_string:
        raise ValueError(
            f"Invalid FY format: {fy_string}. Expected format: YYYY-YY (e.g., 2025-26)"
        )

    parts = fy_string.split("-")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid FY format: {fy_string}. Expected format: YYYY-YY (e.g., 2025-26)"
        )

    try:
        start_year = int(parts[0])
        end_year_short = int(parts[1])

        # Validate that end_year_short is start_year + 1 (last two digits)
        expected_end_year_short = (start_year + 1) % 100
        if end_year_short != expected_end_year_short:
            raise ValueError(
                f"Invalid FY format: {fy_string}. End year {end_year_short:02d} "
                f"does not match start year {start_year} (expected {(start_year + 1) % 100:02d})"
            )

        # UK FY: April 6, YYYY to April 5, YYYY+1
        # Make timezone-aware (UTC) to match transaction times
        start_date = datetime(start_year, 4, 6, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(start_year + 1, 4, 5, 23, 59, 59, 999999, tzinfo=UTC)

        return start_date, end_date

    except ValueError as e:
        if "Invalid FY format" in str(e):
            raise
        raise ValueError(f"Invalid FY format: {fy_string}. {e}") from e


def is_event_in_fy_range(
    transaction_time: str, fy_start: datetime | None, fy_end: datetime | None
) -> bool:
    """
    Check if transaction date falls within FY range.

    Args:
        transaction_time: ISO timestamp string (e.g., "2020-07-07T13:33:15.023Z")
        fy_start: FY start date (datetime) or None for all-time analysis
        fy_end: FY end date (datetime) or None for all-time analysis

    Returns:
        True if transaction date is within FY range (or always True for all-time),
        False otherwise
    """
    # If no date range specified, include all events (all-time analysis)
    if fy_start is None or fy_end is None:
        return True

    try:
        # Parse ISO timestamp (will be timezone-aware)
        dt = datetime.fromisoformat(transaction_time.replace("Z", "+00:00"))
        # Compare dates (both should be timezone-aware now)
        return fy_start <= dt <= fy_end
    except (ValueError, AttributeError):
        return False


def calculate_fy_gains_per_symbol(
    fy_start: datetime | None,
    fy_end: datetime | None,
    input_file: str,
    splits_file: str | None = None,
    name_changes_file: str | None = None,
) -> dict[str, float]:
    """
    Calculate capital gains per symbol for the specified UK Financial Year.

    Processes ALL events from day 0 to maintain accurate cost basis, but only
    counts profits from taxable events that occur within the FY date range.

    Args:
        fy_start: FY start date (datetime)
        fy_end: FY end date (datetime)
        input_file: Path to analyzed events JSON file
        splits_file: Optional path to splits.json file
        name_changes_file: Optional path to name_changes.json file

    Returns:
        Dictionary mapping symbol -> total profit for FY period
    """
    # Check if input file exists
    input_path = Path(input_file)
    if not input_path.exists():
        error_msg = f"Error: Input file not found: {input_file}\n"
        error_msg += "Please run the analyzer first to generate the analyzed events file.\n"
        raise FileNotFoundError(error_msg)

    # Load analyzed events (ALL events, not filtered by date)
    print(f"Loading and analyzing events from {input_file}...")
    all_events = analyze_events(input_file)

    if not all_events:
        print("No events found")
        return {}

    # Set up file paths
    if name_changes_file is None:
        name_changes_file = str(input_path.parent / "name_changes.json")

    if splits_file is None:
        splits_file = str(input_path.parent / "splits.json")

    # Load name changes and splits
    name_changes_mapping = load_name_changes(name_changes_file)
    splits_by_symbol = load_splits(splits_file)
    if splits_by_symbol:
        print(f"Loaded splits for {len(splits_by_symbol)} symbols")

    # Normalize all symbols to their latest names
    symbol_to_latest: dict[str, str] = {}
    for event in all_events:
        symbol = event.get("symbol", "").upper()
        if symbol:
            latest_symbol, _, _ = resolve_symbol(symbol, name_changes_mapping)
            symbol_to_latest[symbol] = latest_symbol
            event["symbol"] = latest_symbol

    # Group events by normalized symbol
    events_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in all_events:
        symbol = event.get("symbol", "").upper()
        if symbol:
            events_by_symbol[symbol].append(event)

    # Sort events by transaction_time for each symbol
    for symbol in events_by_symbol:
        events_by_symbol[symbol].sort(key=lambda x: x.get("transaction_time", ""))

    print(f"Processing {len(events_by_symbol)} unique symbols...")

    # Track gains per symbol (only for FY period)
    gains_by_symbol: dict[str, float] = defaultdict(float)

    # Process each symbol
    for symbol, symbol_events in events_by_symbol.items():
        # Track position state for this symbol
        position = 0.0
        cost_basis = 0.0
        avg_cost = 0.0
        last_processed_date: str | None = None

        # Process ALL events chronologically (from day 0)
        for event in symbol_events:
            side = event.get("side", "").lower()
            qty = float(event.get("qty", 0))
            price = float(event.get("price", 0))
            transaction_time = event.get("transaction_time", "")

            # Extract date from transaction_time
            event_date = (
                transaction_time.split("T")[0] if "T" in transaction_time else transaction_time[:10]
            )

            # Apply any splits that occurred between last event and this event
            position, cost_basis, avg_cost, _ = apply_splits(
                position,
                cost_basis,
                avg_cost,
                symbol,
                event_date,
                splits_by_symbol,
                last_processed_date,
            )

            # Update last processed date
            last_processed_date = event_date

            # Track previous state (after split adjustments)
            prev_cost_basis = cost_basis

            # Initialize profit
            profit = None
            is_taxable_event = False

            # Normalize side
            if side in ["sell_short", "sell"]:
                side = "sell"

            # Check if this event is within FY range (for counting profits)
            in_fy_range = is_event_in_fy_range(transaction_time, fy_start, fy_end)

            # Process buy or sell
            if side == "buy":
                # Buying: handle covering shorts and creating long positions
                if position < 0:
                    # We have a short position - need to cover
                    short_qty = abs(position)
                    if qty <= short_qty:
                        # Covering part or all of the short (TAXABLE EVENT)
                        short_cost_basis_portion = (
                            (qty / short_qty) * abs(cost_basis) if cost_basis < 0 else 0
                        )
                        cover_cost = qty * price
                        profit = short_cost_basis_portion - cover_cost

                        cost_basis += cover_cost
                        position += qty

                        if position == 0:
                            avg_cost = 0
                        else:
                            avg_cost = abs(cost_basis / position) if position != 0 else 0

                        is_taxable_event = True

                    else:
                        # Covering short and creating long position
                        excess_qty = qty - short_qty

                        # Close short position (TAXABLE EVENT)
                        short_proceeds = abs(prev_cost_basis) if prev_cost_basis < 0 else 0
                        cover_cost = short_qty * price
                        short_profit = short_proceeds - cover_cost

                        if in_fy_range:
                            gains_by_symbol[symbol] += short_profit

                        # Update state for closing short
                        cost_basis = excess_qty * price
                        position = excess_qty
                        avg_cost = price

                elif position == 0:
                    # Starting new long position (not taxable)
                    cost_basis = qty * price
                    avg_cost = price
                    position = qty
                else:
                    # Adding to existing long position (not taxable)
                    total_cost = cost_basis + (qty * price)
                    position += qty
                    cost_basis = total_cost
                    avg_cost = cost_basis / position if position > 0 else 0

            elif side == "sell":
                # Selling: handle reducing long positions and creating short positions
                if position > 0:
                    # We have a long position
                    if qty < position:
                        # Partial sale (TAXABLE EVENT)
                        sale_cost_basis = (qty / position) * cost_basis
                        sale_proceeds = qty * price
                        profit = sale_proceeds - sale_cost_basis

                        cost_basis -= sale_cost_basis
                        position -= qty
                        avg_cost = cost_basis / position if position > 0 else 0

                        is_taxable_event = True

                    elif qty == position:
                        # Full sale (TAXABLE EVENT)
                        sale_proceeds = qty * price
                        profit = sale_proceeds - cost_basis

                        cost_basis = 0
                        position = 0
                        avg_cost = 0

                        is_taxable_event = True

                    else:
                        # Selling more than position (creates short)
                        long_qty = position
                        excess_qty = qty - position

                        # Close long position (TAXABLE EVENT)
                        long_sale_proceeds = long_qty * price
                        long_profit = long_sale_proceeds - cost_basis

                        if in_fy_range:
                            gains_by_symbol[symbol] += long_profit

                        # Open short position with excess
                        short_proceeds = excess_qty * price
                        cost_basis = -short_proceeds
                        position = -excess_qty
                        avg_cost = price

                elif position == 0:
                    # Selling without position (short sale, not taxable yet)
                    short_proceeds = qty * price
                    cost_basis = -short_proceeds
                    position = -qty
                    avg_cost = price
                else:
                    # We have a short position - increasing the short (not taxable)
                    additional_proceeds = qty * price
                    cost_basis -= additional_proceeds
                    position -= qty
                    avg_cost = abs(cost_basis / position) if position != 0 else 0

            # Count profit if this is a taxable event within FY range
            if is_taxable_event and profit is not None and in_fy_range:
                gains_by_symbol[symbol] += profit

    return dict(gains_by_symbol)


def generate_text_report(
    fy_string: str | None,
    fy_start: datetime | None,
    fy_end: datetime | None,
    gains_by_symbol: dict[str, float],
    output_file: str,
):
    """Generate human-readable text report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate totals
    total_profit = sum(gains_by_symbol.values())
    gains_only = {s: p for s, p in gains_by_symbol.items() if p > 0}
    losses_only = {s: p for s, p in gains_by_symbol.items() if p <= 0}

    # Sort by profit (highest first)
    sorted_gains = sorted(gains_by_symbol.items(), key=lambda x: x[1], reverse=True)

    with open(output_file, "w") as f:
        # Header
        f.write("=" * 80 + "\n")
        if fy_string:
            f.write("UK Financial Year Capital Gains Report\n")
            f.write(
                f"Financial Year: {fy_string} "
                f"({fy_start.strftime('%B %d, %Y')} to {fy_end.strftime('%B %d, %Y')})\n"
            )
        else:
            f.write("All-Time Capital Gains Report\n")
            f.write("Period: All trading events from day 0\n")
        f.write("=" * 80 + "\n\n")

        # Summary
        f.write("Summary:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Profit/Loss: {format_currency(total_profit)}\n")
        f.write(f"Number of Symbols with Gains: {len(gains_only)}\n")
        f.write(f"Number of Symbols with Losses: {len(losses_only)}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Detailed table
        if sorted_gains:
            f.write("Gains by Symbol (sorted by profit, highest first):\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Symbol':<15} {'Profit/Loss':>20}\n")
            f.write("-" * 80 + "\n")

            for symbol, profit in sorted_gains:
                f.write(f"{symbol:<15} {format_currency(profit):>20}\n")

            f.write("-" * 80 + "\n\n")

        # Sections for gains and losses
        if gains_only:
            f.write("Symbols with Gains:\n")
            f.write("-" * 80 + "\n")
            sorted_gains_only = sorted(gains_only.items(), key=lambda x: x[1], reverse=True)
            for symbol, profit in sorted_gains_only:
                f.write(f"{symbol:<15} {format_currency(profit):>20}\n")
            f.write("\n")

        if losses_only:
            f.write("Symbols with Losses:\n")
            f.write("-" * 80 + "\n")
            sorted_losses_only = sorted(losses_only.items(), key=lambda x: x[1])
            for symbol, profit in sorted_losses_only:
                f.write(f"{symbol:<15} {format_currency(profit):>20}\n")
            f.write("\n")

    print(f"Text report written to {output_file}")


def generate_json_report(
    fy_string: str | None,
    fy_start: datetime | None,
    fy_end: datetime | None,
    gains_by_symbol: dict[str, float],
    output_file: str,
):
    """Generate JSON report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by profit (highest first)
    sorted_gains = sorted(gains_by_symbol.items(), key=lambda x: x[1], reverse=True)

    report_data: dict[str, Any] = {
        "total_profit_loss": sum(gains_by_symbol.values()),
        "gains_by_symbol": [
            {"symbol": symbol, "profit_loss": profit} for symbol, profit in sorted_gains
        ],
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "num_symbols": len(gains_by_symbol),
        },
    }

    if fy_string:
        report_data["financial_year"] = fy_string
        report_data["period"] = {
            "start_date": fy_start.isoformat(),
            "end_date": fy_end.isoformat(),
        }
    else:
        report_data["period"] = "all-time"

    with open(output_file, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"JSON report written to {output_file}")


def generate_csv_report(
    fy_string: str | None,
    gains_by_symbol: dict[str, float],
    output_file: str,
):
    """Generate CSV report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by profit (highest first)
    sorted_gains = sorted(gains_by_symbol.items(), key=lambda x: x[1], reverse=True)

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Symbol", "Profit/Loss"])

        for symbol, profit in sorted_gains:
            writer.writerow([symbol, profit])

    print(f"CSV report written to {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate UK Financial Year or all-time capital gains report across all symbols"
    )
    parser.add_argument(
        "fy",
        type=str,
        nargs="?",
        default=None,
        help=(
            'UK Financial Year (e.g., "2025-26" for April 6, 2025 to April 5, 2026). '
            "If omitted, performs all-time analysis."
        ),
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="Path to input analyzed events JSON file (overrides default)",
    )
    parser.add_argument(
        "--splits",
        "-s",
        type=str,
        help="Path to splits.json file (overrides default)",
    )
    parser.add_argument(
        "--name-changes",
        "-n",
        type=str,
        help="Path to name_changes.json file (overrides default)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        help="Output directory (overrides default: data/tax-return/reports/)",
    )

    args = parser.parse_args()

    # Validate and parse FY (or set to all-time)
    fy_start: datetime | None = None
    fy_end: datetime | None = None
    fy_string: str | None = None

    if args.fy:
        try:
            fy_start, fy_end = parse_fy_date_range(args.fy)
            fy_string = args.fy
            print(f"Financial Year: {args.fy}")
            print(f"Period: {fy_start.strftime('%B %d, %Y')} to {fy_end.strftime('%B %d, %Y')}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("All-Time Analysis: Processing all events from day 0")

    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent

    # Set default paths
    if args.input:
        input_file = Path(args.input)
    else:
        input_file = (
            project_root
            / "data"
            / "trading"
            / "alpaca"
            / "live"
            / "taxable_activities_analyzed.json"
        )

    splits_file = None
    if args.splits:
        splits_file = str(Path(args.splits))
    else:
        splits_file = str(input_file.parent / "splits.json")

    name_changes_file = None
    if args.name_changes:
        name_changes_file = str(Path(args.name_changes))
    else:
        name_changes_file = str(input_file.parent / "name_changes.json")

    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / "data" / "tax-return" / "reports"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate FY gains
    try:
        gains_by_symbol = calculate_fy_gains_per_symbol(
            fy_start, fy_end, str(input_file), splits_file, name_changes_file
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if not gains_by_symbol:
        period_desc = f"Financial Year {args.fy}" if args.fy else "all-time period"
        print(f"No taxable events found for the specified {period_desc}.")
        sys.exit(0)

    # Generate reports
    if fy_string:
        base_filename = f"FY_{fy_string}_capital_gains_report"
        report_title = f"FY {fy_string}"
    else:
        base_filename = "all_time_capital_gains_report"
        report_title = "All-Time"

    text_file = output_dir / f"{base_filename}.txt"
    json_file = output_dir / f"{base_filename}.json"
    csv_file = output_dir / f"{base_filename}.csv"

    generate_text_report(fy_string, fy_start, fy_end, gains_by_symbol, str(text_file))
    generate_json_report(fy_string, fy_start, fy_end, gains_by_symbol, str(json_file))
    generate_csv_report(fy_string, gains_by_symbol, str(csv_file))

    # Print summary
    total_profit = sum(gains_by_symbol.values())
    print(f"\n{'=' * 80}")
    print(f"Report Summary for {report_title}:")
    print(f"{'=' * 80}")
    print(f"Total Profit/Loss: {format_currency(total_profit)}")
    print(f"Number of Symbols: {len(gains_by_symbol)}")
    print("Reports generated:")
    print(f"  - {text_file}")
    print(f"  - {json_file}")
    print(f"  - {csv_file}")


if __name__ == "__main__":
    main()
