#!/usr/bin/env python3
"""
Script to generate UK Financial Year or all-time dividend reports.
Processes dividend data from Alpaca API and generates reports in txt, json, and csv formats.
Supports both USD-only and USD-GBP conversion.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fx_utils import GBPConversionInfo, get_gbp_conversion_info

try:
    # Preferred: provided by the installed exchange-rate package
    from exchange_rate_config import get_default_provider
except ImportError:  # pragma: no cover - fallback to direct src path
    project_root_for_fx = Path(__file__).parent.parent.parent.parent
    fx_src_path = project_root_for_fx / "packages" / "exchange_rate" / "src"
    if str(fx_src_path) not in sys.path:
        sys.path.insert(0, str(fx_src_path))
    from exchange_rate_config import get_default_provider

from balance_tracker import format_currency
from fiscal_year_report import parse_fy_date_range


@dataclass
class DividendGBP:
    """Represents a single dividend with original and GBP values."""

    date: str
    symbol: str
    net_amount: float
    net_amount_gbp: float
    per_share_amount: float | None
    description: str | None
    fx: GBPConversionInfo | None


def find_latest_dividends_file(base_dir: Path) -> Path | None:
    """
    Find the most recent dividends.json file in timestamped folders or directly in base_dir.

    Args:
        base_dir: Base directory containing timestamped folders (e.g., data/dividends/alpaca/live)

    Returns:
        Path to the most recent dividends.json file, or None if not found
    """
    if not base_dir.exists():
        return None

    # First, check if dividends.json exists directly in base_dir
    direct_file = base_dir / "dividends.json"
    if direct_file.exists():
        return direct_file

    # Find all timestamped folders (YYYY-MM-DD format)
    date_folders = []
    for item in base_dir.iterdir():
        if item.is_dir() and len(item.name) == 10:  # YYYY-MM-DD format
            try:
                # Validate it's a valid date
                datetime.strptime(item.name, "%Y-%m-%d")
                dividends_file = item / "dividends.json"
                if dividends_file.exists():
                    date_folders.append((item.name, dividends_file))
            except ValueError:
                continue

    if not date_folders:
        return None

    # Sort by date (most recent first)
    date_folders.sort(key=lambda x: x[0], reverse=True)
    return date_folders[0][1]


def load_dividends(input_file: str) -> list[dict[str, Any]]:
    """
    Load dividends from JSON file.

    Args:
        input_file: Path to dividends.json file

    Returns:
        List of dividend dictionaries

    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Error: Input file not found: {input_file}")

    print(f"Loading dividends from {input_file}...")
    with open(input_path) as f:
        dividends = json.load(f)

    if not isinstance(dividends, list):
        raise ValueError(f"Expected dividends to be a list, got {type(dividends)}")

    print(f"Loaded {len(dividends)} dividend records")
    return dividends


def is_dividend_in_fy_range(
    dividend_date: str, fy_start: datetime | None, fy_end: datetime | None
) -> bool:
    """
    Check if dividend date falls within FY range.

    Args:
        dividend_date: Date string in YYYY-MM-DD format
        fy_start: FY start date (datetime) or None for all-time analysis
        fy_end: FY end date (datetime) or None for all-time analysis

    Returns:
        True if dividend date is within FY range (or always True for all-time),
        False otherwise
    """
    # If no date range specified, include all dividends (all-time analysis)
    if fy_start is None or fy_end is None:
        return True

    try:
        # Parse date string and make it timezone-aware for comparison
        dt = datetime.strptime(dividend_date, "%Y-%m-%d").replace(tzinfo=UTC)
        # Compare dates (both should be timezone-aware now)
        return fy_start <= dt <= fy_end
    except (ValueError, AttributeError):
        return False


def calculate_dividends(
    dividends: list[dict[str, Any]],
    fy_start: datetime | None,
    fy_end: datetime | None,
    fx_provider: str | None = None,
    base_currency: str = "USD",
) -> tuple[dict[str, float], dict[str, float], list[DividendGBP], dict[str, Any]]:
    """
    Calculate dividend totals per symbol and convert to GBP if provider specified.

    Args:
        dividends: List of dividend dictionaries
        fy_start: FY start date (datetime) or None for all-time
        fy_end: FY end date (datetime) or None for all-time
        fx_provider: Optional FX provider name for GBP conversion
        base_currency: Base currency (default: USD)

    Returns:
        Tuple of:
        - dividends_by_symbol: dict mapping symbol -> total USD amount
        - dividends_by_symbol_gbp: dict mapping symbol -> total GBP amount
        - dividends_gbp: list of DividendGBP objects
        - fx_metadata: dict with FX conversion metadata
    """
    dividends_by_symbol: dict[str, float] = defaultdict(float)
    dividends_by_symbol_gbp: dict[str, float] = defaultdict(float)
    dividends_gbp: list[DividendGBP] = []
    fx_metadata: dict[str, Any] = {
        "provider": fx_provider,
        "base_currency": base_currency,
        "target_currency": "GBP",
        "dates_used": set(),
        "missing_rate_dates": set(),
        "all_rates_available": True,
    }

    for div in dividends:
        # Get dividend date
        dividend_date = div.get("date", "")
        if not dividend_date:
            continue

        # Filter by fiscal year if specified
        if not is_dividend_in_fy_range(dividend_date, fy_start, fy_end):
            continue

        # Get dividend amount
        net_amount_str = div.get("net_amount", "0")
        try:
            net_amount = float(net_amount_str)
        except (ValueError, TypeError):
            continue

        symbol = div.get("symbol", "")
        if not symbol:
            continue

        # Add to totals
        dividends_by_symbol[symbol] += net_amount

        # Convert to GBP if provider specified
        fx_info: GBPConversionInfo | None = None
        net_amount_gbp = 0.0
        if fx_provider:
            # Use dividend date for FX lookup
            fx_info = get_gbp_conversion_info(
                transaction_time=dividend_date,
                provider_name=fx_provider,
                from_currency=base_currency,
                to_currency="GBP",
            )
            if fx_info:
                net_amount_gbp = fx_info.convert(net_amount)
                dividends_by_symbol_gbp[symbol] += net_amount_gbp
                fx_metadata["dates_used"].add(fx_info.rate_date)
            else:
                # Mark that FX data is incomplete for this run
                fx_metadata["all_rates_available"] = False
                fx_metadata["missing_rate_dates"].add(dividend_date)

        # Get additional dividend fields
        per_share_amount = None
        per_share_str = div.get("per_share_amount")
        if per_share_str:
            try:
                per_share_amount = float(per_share_str)
            except (ValueError, TypeError):
                pass

        description = div.get("description")

        dividends_gbp.append(
            DividendGBP(
                date=dividend_date,
                symbol=symbol,
                net_amount=net_amount,
                net_amount_gbp=net_amount_gbp,
                per_share_amount=per_share_amount,
                description=description,
                fx=fx_info,
            )
        )

    # Convert sets to sorted lists for JSON-serialisable metadata
    fx_metadata["dates_used"] = sorted(fx_metadata["dates_used"])
    fx_metadata["missing_rate_dates"] = sorted(fx_metadata["missing_rate_dates"])

    return (
        dict(dividends_by_symbol),
        dict(dividends_by_symbol_gbp),
        dividends_gbp,
        fx_metadata,
    )


def generate_text_report(
    fy_string: str | None,
    fy_start: datetime | None,
    fy_end: datetime | None,
    dividends_by_symbol: dict[str, float],
    dividends_by_symbol_gbp: dict[str, float] | None,
    dividends_gbp: list[DividendGBP],
    fx_metadata: dict[str, Any] | None,
    output_file: str,
):
    """Generate human-readable text report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate totals
    total_dividends = sum(dividends_by_symbol.values())
    total_dividends_gbp = sum(dividends_by_symbol_gbp.values()) if dividends_by_symbol_gbp else None

    # Sort dividends by date (oldest first)
    sorted_dividends = sorted(dividends_gbp, key=lambda d: d.date)

    # Sort symbols by total amount (highest first)
    sorted_symbols = sorted(dividends_by_symbol.items(), key=lambda x: x[1], reverse=True)

    with open(output_file, "w") as f:
        # Header
        f.write("=" * 80 + "\n")
        if fy_string:
            f.write("UK Financial Year Dividend Report\n")
            f.write(
                f"Financial Year: {fy_string} "
                f"({fy_start.strftime('%B %d, %Y')} to {fy_end.strftime('%B %d, %Y')})\n"
            )
        else:
            f.write("All-Time Dividend Report\n")
            f.write("Period: All dividends from day 0\n")
        f.write("=" * 80 + "\n\n")

        # Summary
        f.write("Summary:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Dividends: {format_currency(total_dividends)}\n")
        if total_dividends_gbp is not None:
            f.write(f"Total Dividends (GBP): £{total_dividends_gbp:,.2f}\n")
        if fx_metadata and fx_metadata.get("provider"):
            provider = fx_metadata["provider"]
            base_ccy = fx_metadata.get("base_currency", "USD")
            f.write(
                f"FX Provider: {provider} (converting {base_ccy} to GBP using per-day spot rates)\n"
            )
        f.write(f"Number of Symbols: {len(dividends_by_symbol)}\n")
        f.write(f"Number of Dividend Payments: {len(dividends_gbp)}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Notes section (only for GBP reports)
        if dividends_by_symbol_gbp and fx_metadata and fx_metadata.get("provider"):
            provider = fx_metadata["provider"]
            f.write("Notes: \n")
            f.write("-" * 80 + "\n")
            f.write(f"Currency conversion provider: {provider}\n")
            f.write("Exchange rates are per-day spot rates for the dividend payment date.\n")
            f.write(
                "Missing FX data for the chosen provider is fetched on-demand "
                "and cached for future runs.\n"
            )
            f.write("\n")

        # Individual dividends section
        if sorted_dividends:
            f.write("Individual Dividends (sorted by date, oldest first):\n")
            if dividends_by_symbol_gbp:
                header = (
                    f"{'Date':<12} {'Symbol':<15} {'Amount (USD)':>20} "
                    f"{'Amount (GBP)':>20} {'Rate':>12}\n"
                )
                separator_width = len(header.rstrip("\n"))
                f.write("-" * separator_width + "\n")
                f.write(header)
                f.write("-" * separator_width + "\n")

                for div in sorted_dividends:
                    # Get conversion rate if available
                    rate_str = "N/A"
                    if div.fx and div.fx.rate:
                        rate_str = f"{div.fx.rate:.6f}"
                    f.write(
                        f"{div.date:<12} {div.symbol:<15} {format_currency(div.net_amount):>20} "
                        f"{'£' + format(div.net_amount_gbp, ',.2f'):>20} {rate_str:>12}\n"
                    )
                f.write("-" * separator_width + "\n\n")
            else:
                header = f"{'Date':<12} {'Symbol':<15} {'Amount (USD)':>20}\n"
                separator_width = len(header.rstrip("\n"))
                f.write("-" * separator_width + "\n")
                f.write(header)
                f.write("-" * separator_width + "\n")

                for div in sorted_dividends:
                    f.write(
                        f"{div.date:<12} {div.symbol:<15} {format_currency(div.net_amount):>20}\n"
                    )
                f.write("-" * separator_width + "\n\n")

        # Totals by symbol section
        if sorted_symbols:
            f.write("Totals by Symbol (sorted by total amount, highest first):\n")
            if dividends_by_symbol_gbp:
                header = f"{'Symbol':<15} {'Total Amount (USD)':>25} {'Total Amount (GBP)':>25}\n"
                separator_width = len(header.rstrip("\n"))
                f.write("-" * separator_width + "\n")
                f.write(header)
                f.write("-" * separator_width + "\n")

                for symbol, total in sorted_symbols:
                    total_gbp = dividends_by_symbol_gbp.get(symbol, 0.0)
                    f.write(
                        f"{symbol:<15} {format_currency(total):>25} "
                        f"{'£' + format(total_gbp, ',.2f'):>25}\n"
                    )
                f.write("-" * separator_width + "\n")
            else:
                header = f"{'Symbol':<15} {'Total Amount (USD)':>25}\n"
                separator_width = len(header.rstrip("\n"))
                f.write("-" * separator_width + "\n")
                f.write(header)
                f.write("-" * separator_width + "\n")

                for symbol, total in sorted_symbols:
                    f.write(f"{symbol:<15} {format_currency(total):>25}\n")
                f.write("-" * separator_width + "\n")

    print(f"Text report written to {output_file}")


def generate_json_report(
    fy_string: str | None,
    fy_start: datetime | None,
    fy_end: datetime | None,
    dividends_by_symbol: dict[str, float],
    dividends_by_symbol_gbp: dict[str, float] | None,
    dividends_gbp: list[DividendGBP],
    fx_metadata: dict[str, Any] | None,
    output_file: str,
):
    """Generate JSON report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort dividends by date (oldest first)
    sorted_dividends = sorted(dividends_gbp, key=lambda d: d.date)

    # Sort symbols by total amount (highest first)
    sorted_symbols = sorted(dividends_by_symbol.items(), key=lambda x: x[1], reverse=True)

    total_dividends = sum(dividends_by_symbol.values())
    total_dividends_gbp = sum(dividends_by_symbol_gbp.values()) if dividends_by_symbol_gbp else None

    # Count dividends per symbol
    dividend_counts: dict[str, int] = defaultdict(int)
    for div in dividends_gbp:
        dividend_counts[div.symbol] += 1

    report_data: dict[str, Any] = {
        "total_dividends": total_dividends,
        "total_dividends_gbp": total_dividends_gbp,
        "dividends_by_symbol": [],
        "individual_dividends": [],
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "num_symbols": len(dividends_by_symbol),
            "num_dividends": len(dividends_gbp),
        },
    }

    # Add dividends by symbol
    for symbol, total in sorted_symbols:
        entry: dict[str, Any] = {
            "symbol": symbol,
            "total_amount": total,
            "dividend_count": dividend_counts.get(symbol, 0),
        }
        if dividends_by_symbol_gbp:
            entry["total_amount_gbp"] = dividends_by_symbol_gbp.get(symbol, 0.0)
        report_data["dividends_by_symbol"].append(entry)

    # Add individual dividends
    for div in sorted_dividends:
        div_entry: dict[str, Any] = {
            "date": div.date,
            "symbol": div.symbol,
            "net_amount": div.net_amount,
        }
        if dividends_by_symbol_gbp:
            div_entry["net_amount_gbp"] = div.net_amount_gbp
        if div.per_share_amount is not None:
            div_entry["per_share_amount"] = div.per_share_amount
        if div.description:
            div_entry["description"] = div.description
        report_data["individual_dividends"].append(div_entry)

    if fx_metadata:
        # Shallow copy and ensure JSON-serialisable types
        metadata_fx = {
            "provider": fx_metadata.get("provider"),
            "base_currency": fx_metadata.get("base_currency"),
            "target_currency": fx_metadata.get("target_currency"),
            "dates_used": fx_metadata.get("dates_used", []),
            "missing_rate_dates": fx_metadata.get("missing_rate_dates", []),
        }
        report_data["fx_metadata"] = metadata_fx

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
    dividends_by_symbol: dict[str, float],
    dividends_by_symbol_gbp: dict[str, float] | None,
    output_file: str,
):
    """Generate CSV report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by total amount (highest first)
    sorted_symbols = sorted(dividends_by_symbol.items(), key=lambda x: x[1], reverse=True)

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        if dividends_by_symbol_gbp:
            writer.writerow(["Symbol", "Total Amount", "Total Amount (GBP)"])
        else:
            writer.writerow(["Symbol", "Total Amount"])

        for symbol, total in sorted_symbols:
            if dividends_by_symbol_gbp:
                writer.writerow([symbol, total, dividends_by_symbol_gbp.get(symbol, 0.0)])
            else:
                writer.writerow([symbol, total])

    print(f"CSV report written to {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate UK Financial Year or all-time dividend report"
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
        help="Path to dividends.json file (overrides default)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        help="Output directory (overrides default: data/tax-return/reports/)",
    )
    parser.add_argument(
        "--fx-provider",
        type=str,
        default=None,
        help=(
            "Exchange rate provider to use for GBP conversion. "
            "Precedence: --fx-provider > TAX_REPORT_FX_PROVIDER env var > "
            "config/exchange_rates.json default_provider > 'exchangerate_api'."
        ),
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
        print("All-Time Analysis: Processing all dividends from day 0")

    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent

    # Set default input file path
    if args.input:
        input_file = Path(args.input)
    else:
        # Look for most recent dividends.json in timestamped folders
        dividends_base_dir = project_root / "data" / "dividends" / "alpaca" / "live"
        latest_file = find_latest_dividends_file(dividends_base_dir)
        if latest_file:
            input_file = latest_file
            print(f"Using most recent dividends file: {input_file}")
        else:
            print(
                f"Error: No dividends.json file found in {dividends_base_dir}",
                file=sys.stderr,
            )
            print(
                "Please specify --input path or ensure dividends are fetched first.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / "data" / "tax-return" / "reports"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve FX provider using precedence:
    # 1) CLI --fx-provider
    # 2) TAX_REPORT_FX_PROVIDER env var
    # 3) config/exchange_rates.json default_provider
    # 4) hard-coded 'exchangerate_api'
    env_fx_provider = os.getenv("TAX_REPORT_FX_PROVIDER")
    if args.fx_provider:
        resolved_fx_provider = args.fx_provider
    elif env_fx_provider:
        resolved_fx_provider = env_fx_provider
    else:
        resolved_fx_provider = get_default_provider()

    print(f"Using FX provider for GBP conversion: {resolved_fx_provider}")

    # Load dividends
    try:
        dividends = load_dividends(str(input_file))
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if not dividends:
        period_desc = f"Financial Year {args.fy}" if args.fy else "all-time period"
        print(f"No dividends found for the specified {period_desc}.")
        sys.exit(0)

    # Calculate dividends
    try:
        (
            dividends_by_symbol,
            dividends_by_symbol_gbp,
            dividends_gbp,
            fx_metadata,
        ) = calculate_dividends(
            dividends,
            fy_start,
            fy_end,
            fx_provider=resolved_fx_provider,
            base_currency="USD",
        )
    except Exception as e:
        print(f"Error calculating dividends: {e}", file=sys.stderr)
        sys.exit(1)

    if not dividends_by_symbol:
        period_desc = f"Financial Year {args.fy}" if args.fy else "all-time period"
        print(f"No dividends found for the specified {period_desc}.")
        sys.exit(0)

    # Generate reports
    if fy_string:
        base_filename = f"FY_{fy_string}_dividend_report"
    else:
        base_filename = "all_time_dividend_report"

    # Always generate USD-only reports
    usd_text_file = output_dir / f"{base_filename}.USD.txt"
    usd_json_file = output_dir / f"{base_filename}.USD.json"
    usd_csv_file = output_dir / f"{base_filename}.USD.csv"

    generate_text_report(
        fy_string,
        fy_start,
        fy_end,
        dividends_by_symbol,
        dividends_by_symbol_gbp=None,
        dividends_gbp=dividends_gbp,
        fx_metadata=None,
        output_file=str(usd_text_file),
    )
    generate_json_report(
        fy_string,
        fy_start,
        fy_end,
        dividends_by_symbol,
        dividends_by_symbol_gbp=None,
        dividends_gbp=dividends_gbp,
        fx_metadata=None,
        output_file=str(usd_json_file),
    )
    generate_csv_report(
        dividends_by_symbol,
        dividends_by_symbol_gbp=None,
        output_file=str(usd_csv_file),
    )

    # Decide whether we can safely generate GBP-converted mirror reports
    can_generate_gbp = bool(dividends_by_symbol_gbp) and fx_metadata is not None
    if can_generate_gbp:
        all_rates_available = fx_metadata.get("all_rates_available", True)
        if all_rates_available:
            gbp_text_file = output_dir / f"{base_filename}.USD-GBP.txt"
            gbp_json_file = output_dir / f"{base_filename}.USD-GBP.json"
            gbp_csv_file = output_dir / f"{base_filename}.USD-GBP.csv"

            generate_text_report(
                fy_string,
                fy_start,
                fy_end,
                dividends_by_symbol,
                dividends_by_symbol_gbp=dividends_by_symbol_gbp,
                dividends_gbp=dividends_gbp,
                fx_metadata=fx_metadata,
                output_file=str(gbp_text_file),
            )
            generate_json_report(
                fy_string,
                fy_start,
                fy_end,
                dividends_by_symbol,
                dividends_by_symbol_gbp=dividends_by_symbol_gbp,
                dividends_gbp=dividends_gbp,
                fx_metadata=fx_metadata,
                output_file=str(gbp_json_file),
            )
            generate_csv_report(
                dividends_by_symbol,
                dividends_by_symbol_gbp=dividends_by_symbol_gbp,
                output_file=str(gbp_csv_file),
            )
        else:
            print(
                "Warning: Some FX rates are missing. Skipping GBP-converted reports.",
                file=sys.stderr,
            )
            print(
                f"Missing rates for dates: {fx_metadata.get('missing_rate_dates', [])}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
