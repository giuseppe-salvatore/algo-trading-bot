#!/usr/bin/env python3
"""
Script to calculate the total value of assets sold within a UK Financial Year.
Filters all SELL orders (both long sales and short sales) and sums their values.
This is used to determine if tax reporting is required based on disposal value thresholds.

For UK tax purposes, short sales are included as they generate disposal proceeds
that count toward the annual disposal value threshold.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from analyze_events import analyze_events
from balance_tracker import format_currency
from fiscal_year_report import is_event_in_fy_range, parse_fy_date_range
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


@dataclass
class SoldAssetGBP:
    """Represents a single SELL order with original and GBP values."""

    symbol: str
    transaction_time: str
    qty: float
    price: float
    value_usd: float
    value_gbp: float
    fx: GBPConversionInfo | None


def calculate_sold_assets_value(
    fy_start: datetime | None,
    fy_end: datetime | None,
    input_file: str,
    fx_provider: str | None = None,
    base_currency: str = "USD",
) -> tuple[
    dict[str, float],
    dict[str, float],
    list[SoldAssetGBP],
    float,
    float,
    dict[str, Any],
]:
    """
    Calculate total value of all SELL orders within the specified UK Financial Year.

    Args:
        fy_start: FY start date (datetime) or None for all-time analysis
        fy_end: FY end date (datetime) or None for all-time analysis
        input_file: Path to analyzed events JSON file
        fx_provider: Optional FX provider name for GBP conversion
        base_currency: Base currency (default: USD)

    Returns:
        Tuple of:
        - values_by_symbol_usd: dict mapping symbol -> total USD value
        - values_by_symbol_gbp: dict mapping symbol -> total GBP value
        - sold_assets_gbp: list of SoldAssetGBP objects
        - total_value_usd: total value in USD
        - total_value_gbp: total value in GBP
        - fx_metadata: dict with FX conversion metadata
    """
    # Check if input file exists
    input_path = Path(input_file)
    if not input_path.exists():
        error_msg = f"Error: Input file not found: {input_file}\n"
        error_msg += "Please run the analyzer first to generate the analyzed events file.\n"
        raise FileNotFoundError(error_msg)

    # Load analyzed events
    print(f"Loading and analyzing events from {input_file}...")
    all_events = analyze_events(input_file)

    if not all_events:
        print("No events found")
        return {}, {}, [], 0.0, 0.0, {}

    values_by_symbol_usd: dict[str, float] = defaultdict(float)
    values_by_symbol_gbp: dict[str, float] = defaultdict(float)
    sold_assets_gbp: list[SoldAssetGBP] = []

    # FX statistics / metadata
    fx_metadata: dict[str, Any] = {
        "provider": fx_provider,
        "base_currency": base_currency,
        "target_currency": "GBP",
        "dates_used": set(),
        # Becomes False if ANY FX lookup fails for a transaction.
        "all_rates_available": True,
        # Track which dates we failed to obtain a rate for.
        "missing_rate_dates": set(),
    }

    # Process each event
    for event in all_events:
        side = event.get("side", "").lower()
        transaction_time = event.get("transaction_time", "")

        # Filter for SELL orders only (both "sell" and "sell_short")
        if side not in ["sell", "sell_short"]:
            continue

        # Check if this event is within FY range
        if not is_event_in_fy_range(transaction_time, fy_start, fy_end):
            continue

        # Get transaction details
        symbol = event.get("symbol", "").upper()
        if not symbol:
            continue

        try:
            qty = float(event.get("qty", 0))
            price = float(event.get("price", 0))
        except (ValueError, TypeError):
            continue

        # Calculate value (qty × price)
        value_usd = qty * price

        # Add to totals
        values_by_symbol_usd[symbol] += value_usd

        # Convert to GBP if provider specified
        fx_info: GBPConversionInfo | None = None
        value_gbp = 0.0
        if fx_provider:
            fx_info = get_gbp_conversion_info(
                transaction_time=transaction_time,
                provider_name=fx_provider,
                from_currency=base_currency,
                to_currency="GBP",
            )
            if fx_info:
                value_gbp = fx_info.convert(value_usd)
                values_by_symbol_gbp[symbol] += value_gbp
                fx_metadata["dates_used"].add(fx_info.rate_date)
            else:
                # Mark that FX data is incomplete for this run
                fx_metadata["all_rates_available"] = False
                fx_metadata["missing_rate_dates"].add(
                    transaction_time.split("T")[0]
                    if "T" in transaction_time
                    else transaction_time[:10]
                )

        sold_assets_gbp.append(
            SoldAssetGBP(
                symbol=symbol,
                transaction_time=transaction_time,
                qty=qty,
                price=price,
                value_usd=value_usd,
                value_gbp=value_gbp,
                fx=fx_info,
            )
        )

    # Convert sets to sorted lists for JSON-serialisable metadata
    fx_metadata["dates_used"] = sorted(fx_metadata["dates_used"])
    fx_metadata["missing_rate_dates"] = sorted(fx_metadata["missing_rate_dates"])

    # Calculate totals
    total_value_usd = sum(values_by_symbol_usd.values())
    total_value_gbp = sum(values_by_symbol_gbp.values()) if values_by_symbol_gbp else 0.0

    return (
        dict(values_by_symbol_usd),
        dict(values_by_symbol_gbp),
        sold_assets_gbp,
        total_value_usd,
        total_value_gbp,
        fx_metadata,
    )


def generate_text_report(
    fy_string: str | None,
    fy_start: datetime | None,
    fy_end: datetime | None,
    values_by_symbol_usd: dict[str, float],
    values_by_symbol_gbp: dict[str, float] | None,
    sold_assets_gbp: list[SoldAssetGBP],
    fx_metadata: dict[str, Any] | None,
    output_file: str,
):
    """Generate human-readable text report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate totals
    total_value_usd = sum(values_by_symbol_usd.values())
    total_value_gbp = sum(values_by_symbol_gbp.values()) if values_by_symbol_gbp else None

    # Sort transactions by date (oldest first)
    sorted_transactions = sorted(sold_assets_gbp, key=lambda x: x.transaction_time)

    # Sort symbols by total value (highest first)
    sorted_symbols = sorted(values_by_symbol_usd.items(), key=lambda x: x[1], reverse=True)

    with open(output_file, "w") as f:
        # Header
        f.write("=" * 80 + "\n")
        if fy_string:
            f.write("UK Financial Year Assets Sold Value Report\n")
            f.write(
                f"Financial Year: {fy_string} "
                f"({fy_start.strftime('%B %d, %Y')} to {fy_end.strftime('%B %d, %Y')})\n"
            )
        else:
            f.write("All-Time Assets Sold Value Report\n")
            f.write("Period: All SELL orders from day 0\n")
        f.write("=" * 80 + "\n\n")

        # Summary
        f.write("Summary:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Value of Assets Sold: {format_currency(total_value_usd)}\n")
        if total_value_gbp is not None:
            f.write(f"Total Value of Assets Sold (GBP): £{total_value_gbp:,.2f}\n")
        if fx_metadata and fx_metadata.get("provider"):
            provider = fx_metadata["provider"]
            base_ccy = fx_metadata.get("base_currency", "USD")
            f.write(
                f"FX Provider: {provider} (converting {base_ccy} to GBP using per-day spot rates)\n"
            )
            f.write(
                "Note: Missing FX data for the chosen provider is fetched on-demand "
                "and cached for future runs.\n"
            )
        f.write(f"Number of Symbols: {len(values_by_symbol_usd)}\n")
        f.write(f"Number of SELL Transactions: {len(sold_assets_gbp)}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Individual transactions section
        if sorted_transactions:
            f.write("Individual Transactions (sorted by date, oldest first):\n")
            if values_by_symbol_gbp:
                header = (
                    f"{'Date/Time':<20} {'Symbol':<15} {'Qty':<12} {'Price':<12} "
                    f"{'Value (USD)':>20} {'Value (GBP)':>20} {'FX Rate':>12}\n"
                )
                separator_width = len(header.rstrip("\n"))
                f.write("-" * separator_width + "\n")
                f.write(header)
                f.write("-" * separator_width + "\n")

                for trans in sorted_transactions:
                    # Format date/time
                    try:
                        dt = datetime.fromisoformat(trans.transaction_time.replace("Z", "+00:00"))
                        date_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, AttributeError):
                        date_time_str = trans.transaction_time

                    # Get conversion rate if available
                    rate_str = "N/A"
                    if trans.fx and trans.fx.rate:
                        rate_str = f"{trans.fx.rate:.6f}"

                    f.write(
                        f"{date_time_str:<20} {trans.symbol:<15} {trans.qty:<12.4f} "
                        f"{format_currency(trans.price):<12} "
                        f"{format_currency(trans.value_usd):>20} "
                        f"{'£' + format(trans.value_gbp, ',.2f'):>20} {rate_str:>12}\n"
                    )
                f.write("-" * separator_width + "\n\n")
            else:
                header = (
                    f"{'Date/Time':<20} {'Symbol':<15} {'Qty':<12} {'Price':<12} "
                    f"{'Value (USD)':>20}\n"
                )
                separator_width = len(header.rstrip("\n"))
                f.write("-" * separator_width + "\n")
                f.write(header)
                f.write("-" * separator_width + "\n")

                for trans in sorted_transactions:
                    # Format date/time
                    try:
                        dt = datetime.fromisoformat(trans.transaction_time.replace("Z", "+00:00"))
                        date_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, AttributeError):
                        date_time_str = trans.transaction_time

                    f.write(
                        f"{date_time_str:<20} {trans.symbol:<15} {trans.qty:<12.4f} "
                        f"{format_currency(trans.price):<12} "
                        f"{format_currency(trans.value_usd):>20}\n"
                    )
                f.write("-" * separator_width + "\n\n")

        # Totals by symbol section
        if sorted_symbols:
            f.write("Totals by Symbol (sorted by total value, highest first):\n")
            if values_by_symbol_gbp:
                header = f"{'Symbol':<15} {'Total Value (USD)':>25} {'Total Value (GBP)':>25}\n"
                separator_width = len(header.rstrip("\n"))
                f.write("-" * separator_width + "\n")
                f.write(header)
                f.write("-" * separator_width + "\n")

                for symbol, total_usd in sorted_symbols:
                    total_gbp = values_by_symbol_gbp.get(symbol, 0.0)
                    f.write(
                        f"{symbol:<15} {format_currency(total_usd):>25} "
                        f"{'£' + format(total_gbp, ',.2f'):>25}\n"
                    )
                f.write("-" * separator_width + "\n")
            else:
                header = f"{'Symbol':<15} {'Total Value (USD)':>25}\n"
                separator_width = len(header.rstrip("\n"))
                f.write("-" * separator_width + "\n")
                f.write(header)
                f.write("-" * separator_width + "\n")

                for symbol, total_usd in sorted_symbols:
                    f.write(f"{symbol:<15} {format_currency(total_usd):>25}\n")
                f.write("-" * separator_width + "\n")

    print(f"Text report written to {output_file}")


def generate_json_report(
    fy_string: str | None,
    fy_start: datetime | None,
    fy_end: datetime | None,
    values_by_symbol_usd: dict[str, float],
    values_by_symbol_gbp: dict[str, float] | None,
    sold_assets_gbp: list[SoldAssetGBP],
    fx_metadata: dict[str, Any] | None,
    output_file: str,
):
    """Generate JSON report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort transactions by date (oldest first)
    sorted_transactions = sorted(sold_assets_gbp, key=lambda x: x.transaction_time)

    # Sort symbols by total value (highest first)
    sorted_symbols = sorted(values_by_symbol_usd.items(), key=lambda x: x[1], reverse=True)

    total_value_usd = sum(values_by_symbol_usd.values())
    total_value_gbp = sum(values_by_symbol_gbp.values()) if values_by_symbol_gbp else None

    # Count transactions per symbol
    transaction_counts: dict[str, int] = defaultdict(int)
    for trans in sold_assets_gbp:
        transaction_counts[trans.symbol] += 1

    report_data: dict[str, Any] = {
        "total_value_usd": total_value_usd,
        "total_value_gbp": total_value_gbp,
        "values_by_symbol": [],
        "individual_transactions": [],
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "num_symbols": len(values_by_symbol_usd),
            "num_transactions": len(sold_assets_gbp),
        },
    }

    # Add values by symbol
    for symbol, total_usd in sorted_symbols:
        entry: dict[str, Any] = {
            "symbol": symbol,
            "total_value_usd": total_usd,
            "transaction_count": transaction_counts.get(symbol, 0),
        }
        if values_by_symbol_gbp:
            entry["total_value_gbp"] = values_by_symbol_gbp.get(symbol, 0.0)
        report_data["values_by_symbol"].append(entry)

    # Add individual transactions
    for trans in sorted_transactions:
        trans_entry: dict[str, Any] = {
            "transaction_time": trans.transaction_time,
            "symbol": trans.symbol,
            "qty": trans.qty,
            "price": trans.price,
            "value_usd": trans.value_usd,
        }
        if values_by_symbol_gbp:
            trans_entry["value_gbp"] = trans.value_gbp
            if trans.fx:
                trans_entry["fx_rate"] = trans.fx.rate
                trans_entry["fx_rate_date"] = trans.fx.rate_date
        report_data["individual_transactions"].append(trans_entry)

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
    values_by_symbol_usd: dict[str, float],
    values_by_symbol_gbp: dict[str, float] | None,
    sold_assets_gbp: list[SoldAssetGBP],
    output_file: str,
):
    """Generate CSV report."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort transactions by date (oldest first)
    sorted_transactions = sorted(sold_assets_gbp, key=lambda x: x.transaction_time)

    # Sort symbols by total value (highest first)
    sorted_symbols = sorted(values_by_symbol_usd.items(), key=lambda x: x[1], reverse=True)

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)

        # Write individual transactions
        if values_by_symbol_gbp:
            writer.writerow(
                [
                    "Date/Time",
                    "Symbol",
                    "Qty",
                    "Price",
                    "Value (USD)",
                    "Value (GBP)",
                    "FX Rate",
                ]
            )
        else:
            writer.writerow(["Date/Time", "Symbol", "Qty", "Price", "Value (USD)"])

        for trans in sorted_transactions:
            # Format date/time
            try:
                dt = datetime.fromisoformat(trans.transaction_time.replace("Z", "+00:00"))
                date_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                date_time_str = trans.transaction_time

            if values_by_symbol_gbp:
                rate = trans.fx.rate if trans.fx else None
                writer.writerow(
                    [
                        date_time_str,
                        trans.symbol,
                        trans.qty,
                        trans.price,
                        trans.value_usd,
                        trans.value_gbp if trans.value_gbp > 0 else "",
                        rate if rate else "",
                    ]
                )
            else:
                writer.writerow(
                    [date_time_str, trans.symbol, trans.qty, trans.price, trans.value_usd]
                )

        # Add empty row before summary
        writer.writerow([])

        # Write summary by symbol
        if values_by_symbol_gbp:
            writer.writerow(["Symbol", "Total Value (USD)", "Total Value (GBP)"])
        else:
            writer.writerow(["Symbol", "Total Value (USD)"])

        for symbol, total_usd in sorted_symbols:
            if values_by_symbol_gbp:
                total_gbp = values_by_symbol_gbp.get(symbol, 0.0)
                writer.writerow([symbol, total_usd, total_gbp])
            else:
                writer.writerow([symbol, total_usd])

        # Add grand total row
        writer.writerow([])
        total_value_usd = sum(values_by_symbol_usd.values())
        if values_by_symbol_gbp:
            total_value_gbp = sum(values_by_symbol_gbp.values())
            writer.writerow(["TOTAL", total_value_usd, total_value_gbp])
        else:
            writer.writerow(["TOTAL", total_value_usd])

    print(f"CSV report written to {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Calculate total value of assets sold within a UK Financial Year"
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
        print("All-Time Analysis: Processing all SELL orders from day 0")

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

    # Calculate sold assets value
    try:
        (
            values_by_symbol_usd,
            values_by_symbol_gbp,
            sold_assets_gbp,
            total_value_usd,
            total_value_gbp,
            fx_metadata,
        ) = calculate_sold_assets_value(
            fy_start,
            fy_end,
            str(input_file),
            fx_provider=resolved_fx_provider,
            base_currency="USD",
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if not values_by_symbol_usd:
        period_desc = f"Financial Year {args.fy}" if args.fy else "all-time period"
        print(f"No SELL orders found for the specified {period_desc}.")
        sys.exit(0)

    # Generate reports
    if fy_string:
        base_filename = f"FY_{fy_string}_assets_sold_value"
        report_title = f"FY {fy_string}"
    else:
        base_filename = "all_time_assets_sold_value"
        report_title = "All-Time"

    # Always generate USD-only reports to ensure we have a stable baseline,
    # regardless of FX provider availability.
    usd_text_file = output_dir / f"{base_filename}.USD.txt"
    usd_json_file = output_dir / f"{base_filename}.USD.json"
    usd_csv_file = output_dir / f"{base_filename}.USD.csv"

    generate_text_report(
        fy_string,
        fy_start,
        fy_end,
        values_by_symbol_usd,
        values_by_symbol_gbp=None,
        sold_assets_gbp=sold_assets_gbp,
        fx_metadata=None,
        output_file=str(usd_text_file),
    )
    generate_json_report(
        fy_string,
        fy_start,
        fy_end,
        values_by_symbol_usd,
        values_by_symbol_gbp=None,
        sold_assets_gbp=sold_assets_gbp,
        fx_metadata=None,
        output_file=str(usd_json_file),
    )
    generate_csv_report(
        values_by_symbol_usd,
        values_by_symbol_gbp=None,
        sold_assets_gbp=sold_assets_gbp,
        output_file=str(usd_csv_file),
    )

    # Decide whether we can safely generate GBP-converted mirror reports.
    can_generate_gbp = bool(values_by_symbol_gbp) and fx_metadata is not None
    if can_generate_gbp:
        all_rates_available = fx_metadata.get("all_rates_available", True)
    else:
        all_rates_available = False

    gbp_text_file = None
    gbp_json_file = None
    gbp_csv_file = None

    if can_generate_gbp and all_rates_available:
        gbp_text_file = output_dir / f"{base_filename}.USD-GBP.txt"
        gbp_json_file = output_dir / f"{base_filename}.USD-GBP.json"
        gbp_csv_file = output_dir / f"{base_filename}.USD-GBP.csv"

        generate_text_report(
            fy_string,
            fy_start,
            fy_end,
            values_by_symbol_usd,
            values_by_symbol_gbp,
            sold_assets_gbp,
            fx_metadata,
            str(gbp_text_file),
        )
        generate_json_report(
            fy_string,
            fy_start,
            fy_end,
            values_by_symbol_usd,
            values_by_symbol_gbp,
            sold_assets_gbp,
            fx_metadata,
            str(gbp_json_file),
        )
        generate_csv_report(
            values_by_symbol_usd,
            values_by_symbol_gbp,
            sold_assets_gbp,
            str(gbp_csv_file),
        )
    elif can_generate_gbp and not all_rates_available:
        # Informative warning: we had some GBP data but FX coverage is incomplete,
        # so we intentionally skip writing USD-GBP reports.
        missing_dates = fx_metadata.get("missing_rate_dates", [])
        print(
            "Warning: Skipping GBP-converted reports because some FX rates are missing "
            f"for provider {fx_metadata.get('provider')!r}. "
            f"Missing dates (sample): {missing_dates[:10]}",
            file=sys.stderr,
        )

    # Print summary
    print(f"\n{'=' * 80}")
    print(f"Report Summary for {report_title}:")
    print(f"{'=' * 80}")
    print(f"Total Value of Assets Sold: {format_currency(total_value_usd)}")
    if total_value_gbp is not None:
        print(f"Total Value of Assets Sold (GBP): £{total_value_gbp:,.2f}")
    print(f"Number of Symbols: {len(values_by_symbol_usd)}")
    print(f"Number of SELL Transactions: {len(sold_assets_gbp)}")
    print("Reports generated:")
    print(f"  - {usd_text_file}")
    print(f"  - {usd_json_file}")
    print(f"  - {usd_csv_file}")
    if gbp_text_file and gbp_json_file and gbp_csv_file:
        print(f"  - {gbp_text_file}")
        print(f"  - {gbp_json_file}")
        print(f"  - {gbp_csv_file}")


if __name__ == "__main__":
    main()
