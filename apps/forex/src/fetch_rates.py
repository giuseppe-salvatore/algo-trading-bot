#!/usr/bin/env python3
"""
Fetch exchange rates for a date range.

Usage:
    fetch_rates.py <start-date> <end-date> <currency_pair>

Arguments:
    start-date: Start date in DD-MM-YYYY format (e.g., 15-01-2024)
    end-date: End date in DD-MM-YYYY format (e.g., 20-01-2024)
    currency_pair: Currency pair in FROM/TO format (e.g., USD/GBP)

Examples:
    fetch_rates.py 15-01-2024 20-01-2024 USD/GBP
    fetch_rates.py 01-01-2024 31-01-2024 USD/GBP
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

# Import from exchange_rate package
# In PDM workspace, packages are available via workspace
try:
    from exchange_rate import get_exchange_rates
except ImportError:
    # Fallback: add project root to path if not in workspace context
    # When package-dir = "src", add src directory to path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root / "packages" / "exchange_rate" / "src"))
    from exchange_rate import get_exchange_rates


def parse_date(date_str: str) -> date:
    """
    Parse date from DD-MM-YYYY format.

    Args:
        date_str: Date string in DD-MM-YYYY format

    Returns:
        date object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        day, month, year = map(int, date_str.split("-"))
        return date(year, month, day)
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Invalid date format: {date_str}. Expected DD-MM-YYYY (e.g., 15-01-2024)"
        ) from e


def parse_currency_pair(currency_pair: str) -> tuple[str, str]:
    """
    Parse currency pair from string.

    Supports formats:
    - USD/GBP
    - USD-GBP
    - USD_GBP

    Args:
        currency_pair: Currency pair string

    Returns:
        Tuple of (from_currency, to_currency)

    Raises:
        ValueError: If format is invalid
    """
    # Try different separators
    for separator in ["/", "-", "_"]:
        if separator in currency_pair:
            parts = currency_pair.split(separator, 1)
            if len(parts) == 2:
                from_curr = parts[0].strip().upper()
                to_curr = parts[1].strip().upper()
                if from_curr and to_curr:
                    return from_curr, to_curr

    raise ValueError(
        f"Invalid currency pair format: {currency_pair}. "
        f"Expected FROM/TO format (e.g., USD/GBP, USD-GBP, or USD_GBP)"
    )


def generate_date_range(start_date: date, end_date: date) -> list[date]:
    """
    Generate list of dates from start to end (inclusive).

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        List of date objects

    Raises:
        ValueError: If start_date is after end_date
    """
    if start_date > end_date:
        raise ValueError(
            f"Start date ({start_date}) must be before or equal to end date ({end_date})"
        )

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)

    return dates


def format_rate_output(rate_data: dict) -> str:
    """
    Format rate data for output.

    Args:
        rate_data: Rate dictionary from get_exchange_rates

    Returns:
        Formatted string
    """
    return (
        f"{rate_data['date']} | {rate_data['currency_pair']} | "
        f"{rate_data['rate']:.6f} | {rate_data['source']}"
    )


def main():
    """Main entry point for fetch_rates script."""
    parser = argparse.ArgumentParser(
        description="Fetch exchange rates for a date range",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fetch-rates 15-01-2024 20-01-2024 USD/GBP
  fetch-rates 01-01-2024 31-01-2024 USD/GBP
  fetch-rates 15-01-2024 20-01-2024 USD-GBP
        """,
    )
    parser.add_argument(
        "start_date",
        type=str,
        help="Start date in DD-MM-YYYY format (e.g., 15-01-2024)",
    )
    parser.add_argument(
        "end_date",
        type=str,
        help="End date in DD-MM-YYYY format (e.g., 20-01-2024)",
    )
    parser.add_argument(
        "currency_pair",
        type=str,
        help="Currency pair in FROM/TO format (e.g., USD/GBP, USD-GBP, or USD_GBP)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="exchangerate_api",
        help="Exchange rate provider to use (default: exchangerate_api)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (CSV format). If not specified, prints to stdout",
    )

    args = parser.parse_args()

    # Parse arguments
    try:
        start_date = parse_date(args.start_date)
        end_date = parse_date(args.end_date)
        from_currency, to_currency = parse_currency_pair(args.currency_pair)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate date range
    try:
        dates = generate_date_range(start_date, end_date)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching exchange rates for {len(dates)} dates...", file=sys.stderr)
    print(f"Date range: {start_date} to {end_date}", file=sys.stderr)
    print(f"Currency pair: {from_currency}/{to_currency}", file=sys.stderr)
    print(f"Provider: {args.provider}", file=sys.stderr)
    print("", file=sys.stderr)

    # Fetch rates
    rates = get_exchange_rates(
        dates,
        provider=args.provider,
        from_currency=from_currency,
        to_currency=to_currency,
    )

    if not rates:
        print(
            "Error: No rates were fetched. Check your API configuration and network connection.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Prepare output
    output_lines = []
    output_lines.append("Date | Currency Pair | Rate | Source")
    output_lines.append("-" * 60)

    for rate in rates:
        output_lines.append(format_rate_output(rate))

    output_text = "\n".join(output_lines)

    # Output results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(output_text)
        print(f"Results written to {output_path}", file=sys.stderr)
    else:
        print(output_text)

    # Summary
    print("", file=sys.stderr)
    print(
        f"Summary: Fetched {len(rates)} rates out of {len(dates)} requested dates", file=sys.stderr
    )
    if len(rates) < len(dates):
        missing = len(dates) - len(rates)
        print(f"Warning: {missing} dates could not be fetched", file=sys.stderr)


if __name__ == "__main__":
    main()
