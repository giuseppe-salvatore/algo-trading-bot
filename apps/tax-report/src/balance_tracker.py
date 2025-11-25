#!/usr/bin/env python3
"""
Script to track balance/position for a specific symbol from analyzed trading events.
Takes a symbol as input and generates a human-readable report showing:
- Event type (buy/sell)
- Quantity
- Unit price
- Cost basis
- Position status (opened, updated, or closed)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


def format_datetime(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_timestamp


def format_currency(value: float) -> str:
    """Format currency value with 2 decimal places."""
    return f"${value:,.2f}"


def format_number(value: float, decimals: int = 4) -> str:
    """Format number with specified decimal places."""
    return f"{value:,.{decimals}f}"


def track_balance(symbol: str, input_file: str) -> List[Dict[str, Any]]:
    """
    Track balance for a specific symbol from analyzed events.

    Args:
        symbol: Stock symbol to track
        input_file: Path to analyzed events JSON file

    Returns:
        List of processed events with balance information
    """
    # Load analyzed events
    print(f"Loading events from {input_file}...")
    with open(input_file, "r") as f:
        all_events = json.load(f)

    # Filter events for the symbol
    symbol_events = [e for e in all_events if e.get("symbol", "").upper() == symbol.upper()]

    if not symbol_events:
        print(f"No events found for symbol {symbol}")
        return []

    print(f"Found {len(symbol_events)} events for symbol {symbol}")

    # Track position
    position = 0.0  # Current position quantity
    cost_basis = 0.0  # Total cost basis
    avg_cost = 0.0  # Average cost per share
    accumulated_gains = 0.0  # Running total of profits from closed positions

    processed_events = []

    for event in symbol_events:
        side = event.get("side", "").lower()
        qty = float(event.get("qty", 0))
        price = float(event.get("price", 0))
        transaction_time = event.get("transaction_time", "")

        # Determine previous position state
        prev_position = position
        prev_avg_cost = avg_cost
        prev_cost_basis = cost_basis

        # Initialize profit for this transaction (will be calculated during processing)
        profit = None

        # Normalize side (handle sell_short as sell)
        original_side = side
        if side in ["sell_short", "sell"]:
            side = "sell"

        # Process buy or sell
        if side == "buy":
            # Buying: handle covering shorts and creating long positions
            if position < 0:
                # We have a short position - need to cover
                short_qty = abs(position)
                if qty <= short_qty:
                    # Covering part or all of the short
                    # Calculate profit/loss on the shares being covered
                    # Cost basis of short shares being covered (proportional)
                    short_cost_basis_portion = (
                        (qty / short_qty) * abs(cost_basis) if cost_basis < 0 else 0
                    )
                    cover_cost = qty * price
                    profit = short_cost_basis_portion - cover_cost

                    # Cost to cover: we pay money to buy back shares
                    # For shorts, cost_basis is negative (proceeds received)
                    # When covering, we add the cost (making it less negative)
                    cost_basis += cover_cost
                    position += qty  # Reduces negative position

                    if position == 0:
                        # Fully covered
                        avg_cost = 0
                        status = "closed"
                        status_icon = "🔴"
                    else:
                        # Partially covered, still short
                        avg_cost = abs(cost_basis / position) if position != 0 else 0
                        status = "updated"
                        status_icon = "🔄"

                    # Update accumulated gains for partial/full cover
                    accumulated_gains += profit
                else:
                    # Covering short and creating long position
                    # Split into two events: close short position, then open long position
                    excess_qty = qty - short_qty

                    # First event: Close the short position
                    # Proceeds received from short sale (stored as negative cost_basis)
                    short_proceeds = abs(prev_cost_basis) if prev_cost_basis < 0 else 0
                    # Cost to cover
                    cover_cost = short_qty * price
                    short_profit = short_proceeds - cover_cost

                    # Update state for closing short
                    cost_basis = 0
                    position = 0
                    avg_cost = 0
                    status = "closed"
                    status_icon = "🔴"

                    # Update accumulated gains for closed short position
                    accumulated_gains += short_profit

                    # Create first event (closing short position)
                    event_cost_basis_short = short_qty * price
                    processed_events.append(
                        {
                            "event": event,
                            "side": "buy",  # Buying to cover
                            "qty": short_qty,  # Only the short portion
                            "price": price,
                            "event_cost_basis": event_cost_basis_short,
                            "position_after": position,
                            "cost_basis_after": cost_basis,
                            "avg_cost_after": avg_cost,
                            "status": status,
                            "status_icon": status_icon,
                            "transaction_time": transaction_time,
                            "prev_position": prev_position,
                            "prev_avg_cost": prev_avg_cost,
                            "prev_cost_basis": prev_cost_basis,
                            "profit": short_profit,
                            "accumulated_gains": accumulated_gains,
                            "is_split_event": True,
                            "split_part": "close_short",
                        }
                    )

                    # Second event: Open long position with excess
                    cost_basis = excess_qty * price  # New cost basis for long
                    position = excess_qty
                    avg_cost = price
                    status = "opened"
                    status_icon = "🟢"

                    # Create second event (opening long position)
                    event_cost_basis_long = excess_qty * price
                    processed_events.append(
                        {
                            "event": event,
                            "side": "buy",
                            "qty": excess_qty,  # Only the long portion
                            "price": price,
                            "event_cost_basis": event_cost_basis_long,
                            "position_after": position,
                            "cost_basis_after": cost_basis,
                            "avg_cost_after": avg_cost,
                            "status": status,
                            "status_icon": status_icon,
                            "transaction_time": transaction_time,
                            "prev_position": 0,  # Previous position was 0 (after closing short)
                            "prev_avg_cost": 0,
                            "prev_cost_basis": 0,
                            "profit": None,  # No profit on opening a position
                            "accumulated_gains": accumulated_gains,
                            "is_split_event": True,
                            "split_part": "open_long",
                        }
                    )

                    # Skip the normal event creation for this case
                    continue
            elif position == 0:
                # Starting new long position
                cost_basis = qty * price
                avg_cost = price
                position = qty
                status = "opened"
                status_icon = "🟢"
            else:
                # Adding to existing long position (average cost basis)
                total_cost = cost_basis + (qty * price)
                position += qty
                cost_basis = total_cost
                avg_cost = cost_basis / position if position > 0 else 0
                status = "updated"
                status_icon = "🔄"

        elif side == "sell":
            # Selling: handle reducing long positions and creating short positions
            if position > 0:
                # We have a long position
                if qty < position:
                    # Partial sale: reduce position, cost basis proportional
                    # Calculate profit/loss on the shares being sold
                    sale_cost_basis = (qty / position) * cost_basis
                    sale_proceeds = qty * price
                    profit = sale_proceeds - sale_cost_basis

                    # Update position and cost basis
                    cost_basis -= sale_cost_basis
                    position -= qty
                    avg_cost = cost_basis / position if position > 0 else 0
                    status = "updated"
                    status_icon = "🔄"

                    # Update accumulated gains for partial sale
                    accumulated_gains += profit

                    # Update accumulated gains for partial sale
                    accumulated_gains += profit
                elif qty == position:
                    # Full sale: close position
                    # Calculate profit/loss
                    sale_proceeds = qty * price
                    profit = sale_proceeds - cost_basis

                    cost_basis = 0
                    position = 0
                    avg_cost = 0
                    status = "closed"
                    status_icon = "🔴"

                    # Update accumulated gains
                    accumulated_gains += profit
                else:
                    # Selling more than position (creates short)
                    # Split into two events: close long position, then open short position
                    long_qty = position
                    excess_qty = qty - position

                    # First event: Close the long position
                    long_sale_proceeds = long_qty * price
                    long_closed_cost_basis = cost_basis
                    long_profit = long_sale_proceeds - long_closed_cost_basis

                    # Update state for closing long
                    cost_basis = 0
                    position = 0
                    avg_cost = 0
                    status = "closed"
                    status_icon = "🔴"

                    # Update accumulated gains for closed long position
                    accumulated_gains += long_profit

                    # Create first event (closing long position)
                    event_cost_basis_long = long_qty * price
                    processed_events.append(
                        {
                            "event": event,
                            "side": side,
                            "qty": long_qty,  # Only the long portion
                            "price": price,
                            "event_cost_basis": event_cost_basis_long,
                            "position_after": position,
                            "cost_basis_after": cost_basis,
                            "avg_cost_after": avg_cost,
                            "status": status,
                            "status_icon": status_icon,
                            "transaction_time": transaction_time,
                            "prev_position": prev_position,
                            "prev_avg_cost": prev_avg_cost,
                            "prev_cost_basis": prev_cost_basis,
                            "profit": long_profit,
                            "accumulated_gains": accumulated_gains,
                            "is_split_event": True,
                            "split_part": "close_long",
                        }
                    )

                    # Second event: Open short position with excess
                    short_proceeds = excess_qty * price
                    cost_basis = -short_proceeds  # Negative = proceeds received
                    position = -excess_qty
                    avg_cost = price
                    status = "opened"
                    status_icon = "🟢"

                    # Create second event (opening short position)
                    event_cost_basis_short = excess_qty * price
                    processed_events.append(
                        {
                            "event": event,
                            "side": "sell_short",  # Mark as short sale
                            "qty": excess_qty,  # Only the short portion
                            "price": price,
                            "event_cost_basis": event_cost_basis_short,
                            "position_after": position,
                            "cost_basis_after": cost_basis,
                            "avg_cost_after": avg_cost,
                            "status": status,
                            "status_icon": status_icon,
                            "transaction_time": transaction_time,
                            "prev_position": 0,  # Previous position was 0 (after closing long)
                            "prev_avg_cost": 0,
                            "prev_cost_basis": 0,
                            "profit": None,  # No profit on opening a position
                            "accumulated_gains": accumulated_gains,
                            "is_split_event": True,
                            "split_part": "open_short",
                        }
                    )

                    # Skip the normal event creation for this case
                    continue
            elif position == 0:
                # Selling without position (short sale)
                # For shorts, cost_basis is negative (proceeds received)
                short_proceeds = qty * price
                cost_basis = -short_proceeds
                position = -qty
                avg_cost = price
                status = "opened"
                status_icon = "🟢"
            else:
                # We have a short position - increasing the short
                # No profit/loss when increasing a short position (just opening more)
                # Add proceeds (making cost_basis more negative)
                additional_proceeds = qty * price
                cost_basis -= additional_proceeds
                position -= qty  # More negative
                avg_cost = abs(cost_basis / position) if position != 0 else 0
                status = "updated"
                status_icon = "🔄"
                # No profit calculation - this is just increasing the short position
        else:
            # Unknown side - skip this event
            print(
                f"Warning: Unknown side '{side}' for event {event.get('id', 'unknown')}, skipping"
            )
            continue

        # Calculate event cost basis (for this transaction)
        event_cost_basis = qty * price

        # Note: Profit is now calculated during transaction processing above
        # for both partial and full sales. This section only handles edge cases
        # where profit wasn't already calculated (shouldn't happen with current logic)
        if profit is None and status == "closed":
            # Fallback for edge cases (shouldn't normally execute)
            if prev_position > 0:
                # Closing a long position
                sale_proceeds = qty * price
                profit = sale_proceeds - prev_cost_basis
                accumulated_gains += profit
            elif prev_position < 0:
                # Closing a short position
                short_proceeds = abs(prev_cost_basis) if prev_cost_basis < 0 else 0
                cover_cost = qty * price
                profit = short_proceeds - cover_cost
                accumulated_gains += profit

        processed_events.append(
            {
                "event": event,
                "side": side,
                "qty": qty,
                "price": price,
                "event_cost_basis": event_cost_basis,
                "position_after": position,
                "cost_basis_after": cost_basis,
                "avg_cost_after": avg_cost,
                "status": status,
                "status_icon": status_icon,
                "transaction_time": transaction_time,
                "prev_position": prev_position,
                "prev_avg_cost": prev_avg_cost,
                "prev_cost_basis": prev_cost_basis,
                "profit": profit,
                "accumulated_gains": accumulated_gains,
            }
        )

    return processed_events


def generate_report(symbol: str, processed_events: List[Dict[str, Any]], output_file: str):
    """
    Generate human-readable report file.

    Args:
        symbol: Stock symbol
        processed_events: List of processed events with balance info
        output_file: Path to output text file
    """
    if not processed_events:
        print("No events to report")
        return

    with open(output_file, "w") as f:
        # Calculate total profit from all closed positions
        total_profit = sum(pe.get("profit", 0) or 0 for pe in processed_events)

        # Header
        f.write("=" * 80 + "\n")
        f.write(f"Balance Tracker Report for {symbol.upper()}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total Events: {len(processed_events)}\n")
        f.write(f"Total Profit: {format_currency(total_profit)}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Table header
        f.write("-" * 155 + "\n")
        f.write(
            f"{'Date/Time':<20} {'Side':<10} {'Qty':<12} {'Price':<12} {'Cost Basis':<15} {'Status':<10} {'Type':<6} {'Position':<12} {'Avg Cost':<12} {'Profit':<15} {'Accumulated Gains':<18}\n"
        )
        f.write("-" * 155 + "\n")

        # Process each event
        for pe in processed_events:
            event = pe["event"]
            side = pe["side"].upper()
            qty = pe["qty"]
            price = pe["price"]
            event_cost_basis = pe["event_cost_basis"]
            status_icon = pe["status_icon"]
            status = pe["status"]
            position = pe["position_after"]
            avg_cost = pe["avg_cost_after"]

            # Format values
            date_time = format_datetime(pe["transaction_time"])
            qty_str = format_number(qty)
            price_str = format_currency(price)
            cost_basis_str = format_currency(event_cost_basis)
            position_str = format_number(position) if position != 0 else "0"
            # For short positions, avg_cost represents proceeds per share (positive value)
            # For long positions, avg_cost represents cost per share
            avg_cost_str = format_currency(avg_cost) if avg_cost != 0 else "-"

            # Determine position type (only show when position is opened)
            if status == "opened":
                if position > 0:
                    position_type = "LONG"
                elif position < 0:
                    position_type = "SHORT"
                else:
                    position_type = "-"
            else:
                position_type = "-"

            # Format profit (only show when position is closed)
            profit = pe.get("profit")
            if profit is not None:
                profit_str = format_currency(profit)
            else:
                profit_str = "-"

            # Format accumulated gains (only show when it was updated, i.e., when profit is calculated)
            accumulated_gains = pe.get("accumulated_gains", 0.0)
            if profit is not None:
                accumulated_gains_str = format_currency(accumulated_gains)
            else:
                accumulated_gains_str = "-"

            # Write row
            f.write(
                f"{date_time:<20} {side:<10} {qty_str:<12} {price_str:<12} {cost_basis_str:<15} "
                f"{status_icon} {status:<9} {position_type:<6} {position_str:<12} {avg_cost_str:<12} {profit_str:<15} {accumulated_gains_str:<18}\n"
            )

            # Add empty line after closed positions
            if status == "closed":
                f.write("\n")

        f.write("-" * 125 + "\n\n")

        # Summary
        final_position = processed_events[-1]["position_after"]
        final_cost_basis = processed_events[-1]["cost_basis_after"]
        final_avg_cost = processed_events[-1]["avg_cost_after"]

        f.write("Summary:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Final Position: {format_number(final_position)}\n")
        if final_position > 0:
            f.write(f"Final Cost Basis: {format_currency(final_cost_basis)}\n")
            f.write(f"Average Cost per Share: {format_currency(final_avg_cost)}\n")
        elif final_position < 0:
            f.write(f"Short Proceeds: {format_currency(abs(final_cost_basis))}\n")
            f.write(f"Average Proceeds per Share: {format_currency(final_avg_cost)}\n")
        else:
            f.write(f"Final Cost Basis: {format_currency(final_cost_basis)}\n")
        f.write("-" * 80 + "\n")

    print(f"Report written to {output_file}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python balance_tracker.py <SYMBOL>")
        print("Example: python balance_tracker.py AAPL")
        sys.exit(1)

    symbol = sys.argv[1]
    # Get project root (four levels up from this file: src -> tax-report -> apps -> root)
    project_root = Path(__file__).parent.parent.parent.parent
    input_file = project_root / "data" / "taxable_activities_analyzed.json"
    output_file = project_root / "data" / f"{symbol.upper()}_balance_report.txt"

    # Track balance
    processed_events = track_balance(symbol, str(input_file))

    if processed_events:
        # Generate report
        generate_report(symbol, processed_events, str(output_file))
        print(f"\nBalance tracking complete for {symbol.upper()}")
    else:
        print(f"No events found for symbol {symbol}")


if __name__ == "__main__":
    main()
