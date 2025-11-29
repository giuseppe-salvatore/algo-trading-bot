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
# Files are directly in packages/exchange_rate/src/
# In PDM workspace, packages are available via workspace
try:
    # Try importing as a package (if installed via PDM workspace)
    from exchange_rate import get_exchange_rates
except ImportError:
    # Fallback: add src directory to path and import modules directly
    project_root = Path(__file__).parent.parent.parent.parent
    src_path = project_root / "packages" / "exchange_rate" / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    # Import from the modules directly in src/
    from exchange_rate_proxy import get_exchange_rates


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


def format_table(rates: list[dict]) -> str:
    """
    Format rates as an aligned table.

    Args:
        rates: List of rate dictionaries from get_exchange_rates

    Returns:
        Formatted table string
    """
    if not rates:
        return ""

    # Calculate column widths
    date_width = max(len("Date"), max(len(str(rate["date"])) for rate in rates))
    currency_width = max(len("Currency Pair"), max(len(rate["currency_pair"]) for rate in rates))
    rate_width = max(
        len("Rate"),
        max(len(f"{rate['rate']:.6f}") for rate in rates),
    )
    source_width = max(len("Source"), max(len(rate["source"]) for rate in rates))

    # Format header
    header = (
        f"{'Date':<{date_width}} | "
        f"{'Currency Pair':<{currency_width}} | "
        f"{'Rate':>{rate_width}} | "
        f"{'Source':<{source_width}}"
    )

    # Format separator
    separator = "-" * len(header)

    # Format rows
    rows = []
    for rate in rates:
        date_str = str(rate["date"])
        currency_str = rate["currency_pair"]
        rate_str = f"{rate['rate']:.6f}"
        source_str = rate["source"]
        row = (
            f"{date_str:<{date_width}} | "
            f"{currency_str:<{currency_width}} | "
            f"{rate_str:>{rate_width}} | "
            f"{source_str:<{source_width}}"
        )
        rows.append(row)

    return "\n".join([header, separator] + rows)


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
    output_text = format_table(rates)

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
