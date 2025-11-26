#!/usr/bin/env python3
"""
Script to analyze events in taxable_activities.json.
- Groups events by order_id
- Identifies atomic events (single order_id) and adds them to processable list
- Reconciles events with same order_id:
  - Same price: discards partial fill events
  - Different prices: reconciles using qty, cum_qty, and price fields
- Returns sorted list of processable events (by transaction_time, older first)
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def is_partial_fill(event: dict[str, Any]) -> bool:
    """Check if an event is a partial fill."""
    return event.get("type") == "partial_fill" or event.get("order_status") == "partially_filled"


def reconcile_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Reconcile multiple events with the same order_id.

    When prices differ:
    - Calculate weighted average price: (price1 × qty1 + price2 × qty2) / total_qty
    - Use final cum_qty as total quantity
    - Use earliest transaction_time
    """
    if len(events) == 0:
        raise ValueError("Cannot reconcile empty event list")

    if len(events) == 1:
        return events[0]

    # Helper to parse ISO timestamp for proper sorting
    def parse_timestamp(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.min

    # Sort events by transaction_time (properly parsed) to get earliest and latest
    sorted_events = sorted(events, key=lambda x: parse_timestamp(x.get("transaction_time", "")))
    earliest_event = sorted_events[0]

    # Get prices and quantities
    prices = [float(e.get("price", 0)) for e in sorted_events]
    qtys = [float(e.get("qty", 0)) for e in sorted_events]

    # Check if all prices are the same
    if len(set(prices)) == 1:
        # Same price - keep only fill events, discard partial fills
        fill_events = [e for e in sorted_events if not is_partial_fill(e)]
        if fill_events:
            # Use the fill event with the highest cum_qty (should be the final fill)
            # Sort fill events by cum_qty to get the one with the total
            fill_events_by_cum_qty = sorted(
                fill_events, key=lambda x: float(x.get("cum_qty", 0)), reverse=True
            )
            fill_event = fill_events_by_cum_qty[0].copy()
            final_cum_qty = float(fill_event.get("cum_qty", fill_event.get("qty", 0)))
            fill_event["qty"] = str(final_cum_qty)
            fill_event["cum_qty"] = str(final_cum_qty)
            return fill_event
        else:
            # No fill events, only partial fills
            # Use sum of qty values instead of last event's cum_qty
            # because cum_qty can be incorrect in partial fill data
            total_qty = sum(float(e.get("qty", 0)) for e in sorted_events)
            last_event = sorted_events[-1].copy()
            final_cum_qty = total_qty  # Use sum of qty values, not last event's cum_qty
            last_event["qty"] = str(final_cum_qty)
            last_event["cum_qty"] = str(final_cum_qty)
            last_event["type"] = "fill"
            last_event["order_status"] = "filled"
            last_event["leaves_qty"] = "0"
            return last_event

    # Different prices - reconcile using weighted average
    # Get final cum_qty (should be the MAXIMUM cum_qty from all events, not just the last)
    # The last event might not have the highest cum_qty if events are out of order
    all_cum_qtys = [
        float(e.get("cum_qty", e.get("qty", 0)))
        for e in sorted_events
        if e.get("cum_qty") or e.get("qty")
    ]
    final_cum_qty = (
        max(all_cum_qtys)
        if all_cum_qtys
        else float(sorted_events[-1].get("cum_qty", sorted_events[-1].get("qty", 0)))
    )

    # Calculate weighted average price
    total_value = sum(price * qty for price, qty in zip(prices, qtys, strict=True))
    total_qty = sum(qtys)

    if total_qty > 0:
        weighted_avg_price = total_value / total_qty
    else:
        # Fallback to average if qty is 0
        weighted_avg_price = sum(prices) / len(prices)

    # Create reconciled event based on earliest event
    reconciled = earliest_event.copy()
    reconciled["price"] = str(weighted_avg_price)
    reconciled["qty"] = str(final_cum_qty)
    reconciled["cum_qty"] = str(final_cum_qty)
    reconciled["type"] = "fill"
    reconciled["order_status"] = "filled"
    reconciled["leaves_qty"] = "0"

    return reconciled


def analyze_events(input_file: str) -> list[dict[str, Any]]:
    """
    Analyze events from JSON file and return a list of processable events.

    Args:
        input_file: Path to the input JSON file

    Returns:
        List of processable events, sorted by transaction_time (older first)
    """
    # Check if input file exists
    input_path = Path(input_file)
    if not input_path.exists():
        error_msg = f"Error: Input file not found: {input_file}\n"
        error_msg += (
            "Please ensure the taxable_activities.json file exists in the specified location.\n"
        )
        raise FileNotFoundError(error_msg)

    # Load the JSON file
    print(f"Loading events from {input_file}...")
    with open(input_file) as f:
        events = json.load(f)

    print(f"Loaded {len(events)} events")

    # Group events by order_id
    events_by_order_id = defaultdict(list)
    for event in events:
        order_id = event.get("order_id")
        if order_id:
            events_by_order_id[order_id].append(event)

    print(f"Found {len(events_by_order_id)} unique order IDs")

    # Process events
    processable_events = []

    for _order_id, order_events in events_by_order_id.items():
        if len(order_events) == 1:
            # Atomic event - add directly to processable list
            processable_events.append(order_events[0])
        else:
            # Multiple events with same order_id - need reconciliation
            reconciled_event = reconcile_events(order_events)
            processable_events.append(reconciled_event)

    # Sort by transaction_time (older first)
    processable_events.sort(key=lambda x: x.get("transaction_time", ""))

    print(f"Processed {len(processable_events)} processable events")

    return processable_events


def main():
    """Main entry point for analyze_events script."""
    parser = argparse.ArgumentParser(
        description="Analyze trading events from taxable_activities.json"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="Path to input taxable_activities.json file (overrides default)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Path to output analyzed events JSON file (overrides default)",
    )

    args = parser.parse_args()

    # Get project root (four levels up from this file: src -> tax-report -> apps -> root)
    project_root = Path(__file__).parent.parent.parent.parent

    # Set default paths or use overrides
    if args.input:
        input_file = Path(args.input)
    else:
        input_file = (
            project_root / "data" / "trading" / "alpaca" / "live" / "taxable_activities.json"
        )

    if args.output:
        output_file = Path(args.output)
    else:
        output_file = (
            project_root
            / "data"
            / "trading"
            / "alpaca"
            / "live"
            / "taxable_activities_analyzed.json"
        )

    try:
        processable_events = analyze_events(str(input_file))
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)

    # Optionally write to file for inspection
    print(f"\nWriting {len(processable_events)} processable events to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(processable_events, f, indent=4)

    print(f"Done! Created {output_file}")


if __name__ == "__main__":
    main()
