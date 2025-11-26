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

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


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


def load_splits(splits_file: str) -> dict[str, list[dict[str, Any]]]:
    """
    Load splits from JSON file and organize by symbol and date.

    Args:
        splits_file: Path to splits.json file

    Returns:
        Dictionary mapping symbol -> list of splits sorted by date
    """
    try:
        with open(splits_file) as f:
            all_splits = json.load(f)
    except FileNotFoundError:
        print(
            f"Warning: Splits file {splits_file} not found. Continuing without split adjustments."
        )
        return {}

    # Group splits by symbol and date to avoid duplicates
    splits_by_symbol = defaultdict(list)
    processed_splits = set()  # Track (symbol, date) pairs we've already processed

    for split in all_splits:
        symbol = split.get("symbol", "").upper()
        if not symbol:
            continue

        split_date = split.get("date", "")
        split_key = (symbol, split_date)

        # Skip if we've already processed this split
        if split_key in processed_splits:
            continue

        # Parse the description to extract from_qty and to_qty
        description = split.get("description", "")

        # Extract quantities from description
        # Format: "ADD, From QTY:-25, To QTY:1.666666667, Position Value:209.35"
        # or "REMOVE, From QTY:-25, To QTY:1.666666667, Position Value:209.35"
        from_qty = None
        to_qty = None

        if "From QTY:" in description and "To QTY:" in description:
            try:
                # Extract from_qty
                from_start = description.find("From QTY:") + len("From QTY:")
                from_end = description.find(",", from_start)
                if from_end == -1:
                    from_end = description.find(" ", from_start)
                from_qty_str = description[from_start:from_end].strip()
                from_qty = float(from_qty_str)

                # Extract to_qty
                to_start = description.find("To QTY:") + len("To QTY:")
                to_end = description.find(",", to_start)
                if to_end == -1:
                    to_end = len(description)
                to_qty_str = description[to_start:to_end].strip()
                to_qty = float(to_qty_str)
            except (ValueError, IndexError):
                # Fallback: find corresponding REMOVE/ADD pair
                if "REMOVE" in description:
                    from_qty = abs(float(split.get("qty", 0)))
                    # Try to find corresponding ADD entry
                    for other_split in all_splits:
                        if (
                            other_split.get("symbol", "").upper() == symbol
                            and other_split.get("date") == split_date
                            and "ADD" in other_split.get("description", "")
                        ):
                            to_qty = float(other_split.get("qty", 0))
                            break
                elif "ADD" in description:
                    to_qty = float(split.get("qty", 0))
                    # Try to find corresponding REMOVE entry
                    for other_split in all_splits:
                        if (
                            other_split.get("symbol", "").upper() == symbol
                            and other_split.get("date") == split_date
                            and "REMOVE" in other_split.get("description", "")
                        ):
                            from_qty = abs(float(other_split.get("qty", 0)))
                            break

        # If we couldn't parse, skip this split
        if from_qty is None or to_qty is None or abs(from_qty) == 0:
            continue

        # Calculate split ratio (how many new shares you get per old share)
        # For a forward split (e.g., 3:1): from_qty=1, to_qty=3, ratio=3.0
        # (multiply position by 3)
        # For a reverse split (e.g., 1:3): from_qty=3, to_qty=1, ratio=0.333
        # (multiply position by 0.333)
        # The description format: "From QTY:X, To QTY:Y" means X old shares become Y new shares
        # So: ratio = Y / X (new shares per old share)
        # Use absolute values to handle negative quantities in descriptions
        from_qty_abs = abs(from_qty)
        to_qty_abs = abs(to_qty)
        split_ratio = to_qty_abs / from_qty_abs if from_qty_abs != 0 else 1.0

        # Only process ADD entries (or if we have both quantities)
        if "ADD" in description or (from_qty and to_qty):
            splits_by_symbol[symbol].append(
                {
                    "date": split_date,
                    "from_qty": abs(from_qty),
                    "to_qty": abs(to_qty),
                    "ratio": split_ratio,
                }
            )
            processed_splits.add(split_key)

    # Sort splits by date for each symbol
    for symbol in splits_by_symbol:
        splits_by_symbol[symbol].sort(key=lambda x: x["date"])

    return dict(splits_by_symbol)


def apply_splits(
    position: float,
    cost_basis: float,
    avg_cost: float,
    symbol: str,
    current_date: str,
    splits_by_symbol: dict[str, list[dict[str, Any]]],
    last_processed_date: str | None = None,
) -> tuple[float, float, float, list[dict[str, Any]]]:
    """
    Apply any splits that occurred between last_processed_date and current_date.

    Args:
        position: Current position quantity
        cost_basis: Current cost basis
        avg_cost: Current average cost per share
        symbol: Stock symbol
        current_date: Current event date
        splits_by_symbol: Dictionary of splits by symbol
        last_processed_date: Date of last processed event (None if first event)

    Returns:
        Tuple of (adjusted_position, adjusted_cost_basis, adjusted_avg_cost, applied_splits)
        where applied_splits is a list of split information dictionaries
    """
    applied_splits = []

    if position == 0:
        # No position, no split to apply
        return position, cost_basis, avg_cost, applied_splits

    symbol_upper = symbol.upper()
    if symbol_upper not in splits_by_symbol:
        return position, cost_basis, avg_cost, applied_splits

    splits = splits_by_symbol[symbol_upper]

    # Find splits that occurred between last_processed_date and current_date
    for split in splits:
        split_date = split["date"]
        should_apply = False

        # Check if split occurred in the relevant time period
        if last_processed_date is None:
            # First event - check if split occurred before or on this date
            if split_date <= current_date:
                should_apply = True
        else:
            # Check if split occurred between last event and current event
            if last_processed_date < split_date <= current_date:
                should_apply = True

        if should_apply:
            # Store split info before applying
            prev_position = position
            prev_avg_cost = avg_cost
            ratio = split["ratio"]
            from_qty = split["from_qty"]
            to_qty = split["to_qty"]

            # Apply this split
            position = position * ratio
            # Cost basis stays the same (total value doesn't change)
            # Average cost changes: new_avg_cost = old_avg_cost / ratio
            if ratio > 0:
                avg_cost = avg_cost / ratio

            # Store split information
            applied_splits.append(
                {
                    "date": split_date,
                    "from_qty": from_qty,
                    "to_qty": to_qty,
                    "ratio": ratio,
                    "prev_position": prev_position,
                    "prev_avg_cost": prev_avg_cost,
                    "new_position": position,
                    "new_avg_cost": avg_cost,
                    "cost_basis": cost_basis,  # Cost basis doesn't change
                }
            )

    return position, cost_basis, avg_cost, applied_splits


def track_balance(
    symbol: str, input_file: str, splits_file: str | None = None
) -> list[dict[str, Any]]:
    """
    Track balance for a specific symbol from analyzed events.

    Args:
        symbol: Stock symbol to track
        input_file: Path to analyzed events JSON file
        splits_file: Optional path to splits.json file. If None, will look in data directory.

    Returns:
        List of processed events with balance information
    """
    # Check if input file exists
    input_path = Path(input_file)
    if not input_path.exists():
        error_msg = f"Error: Input file not found: {input_file}\n"
        error_msg += "Please run the analyzer first to generate the analyzed events file.\n"
        if "test" in str(input_file):
            error_msg += "For test data, run: just test-analyze\n"
        else:
            error_msg += "For live data, run: just analyze\n"
        raise FileNotFoundError(error_msg)

    # Load analyzed events
    print(f"Loading events from {input_file}...")
    with open(input_file) as f:
        all_events = json.load(f)

    # Filter events for the symbol
    symbol_events = [e for e in all_events if e.get("symbol", "").upper() == symbol.upper()]

    if not symbol_events:
        print(f"No events found for symbol {symbol}")
        return []

    print(f"Found {len(symbol_events)} events for symbol {symbol}")

    # Load splits
    if splits_file is None:
        # Try to find splits.json in the data directory (same as input_file)
        input_path = Path(input_file)
        # input_file is typically in data/ directory, so splits.json should be in the same directory
        splits_file = input_path.parent / "splits.json"

    splits_by_symbol = load_splits(str(splits_file))
    if splits_by_symbol:
        print(f"Loaded splits for {len(splits_by_symbol)} symbols")

    # Track position
    position = 0.0  # Current position quantity
    cost_basis = 0.0  # Total cost basis
    avg_cost = 0.0  # Average cost per share
    accumulated_gains = 0.0  # Running total of profits from closed positions
    last_processed_date: str | None = None

    processed_events = []

    for event in symbol_events:
        side = event.get("side", "").lower()
        qty = float(event.get("qty", 0))
        price = float(event.get("price", 0))
        transaction_time = event.get("transaction_time", "")

        # Extract date from transaction_time (format: YYYY-MM-DDTHH:MM:SSZ)
        event_date = (
            transaction_time.split("T")[0] if "T" in transaction_time else transaction_time[:10]
        )

        # Apply any splits that occurred between last event and this event
        position, cost_basis, avg_cost, applied_splits = apply_splits(
            position,
            cost_basis,
            avg_cost,
            symbol,
            event_date,
            splits_by_symbol,
            last_processed_date,
        )

        # Add split events to processed_events if any splits were applied
        for split_info in applied_splits:
            processed_events.append(
                {
                    "event": None,  # No actual trading event for splits
                    "side": "SPLIT",
                    "qty": 0,  # Not applicable for splits
                    "price": 0,  # Not applicable for splits
                    "event_cost_basis": 0,  # Not applicable for splits
                    "position_after": split_info["new_position"],
                    "cost_basis_after": split_info["cost_basis"],
                    "avg_cost_after": split_info["new_avg_cost"],
                    "status": "split",
                    "status_icon": "🔀",
                    "transaction_time": f"{split_info['date']}T00:00:00Z",  # Use split date
                    "prev_position": split_info["prev_position"],
                    "prev_avg_cost": split_info["prev_avg_cost"],
                    "prev_cost_basis": split_info["cost_basis"],  # Cost basis doesn't change
                    "profit": None,
                    "accumulated_gains": accumulated_gains,
                    "is_split_event": True,
                    "split_info": split_info,  # Store full split information
                }
            )

        # Determine previous position state (after split adjustments)
        prev_position = position
        prev_avg_cost = avg_cost
        prev_cost_basis = cost_basis

        # Update last processed date
        last_processed_date = event_date

        # Initialize profit for this transaction (will be calculated during processing)
        profit = None

        # Normalize side (handle sell_short as sell)
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


def generate_report(symbol: str, processed_events: list[dict[str, Any]], output_file: str):
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

    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

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
        header = (
            f"{'Date/Time':<20} {'Side':<10} {'Qty':<12} {'Price':<12} "
            f"{'Cost Basis':<15} {'Status':<10} {'Type':<6} {'Position':<12} "
            f"{'Avg Cost':<12} {'Profit':<15} {'Accumulated Gains':<18}\n"
        )
        f.write(header)
        f.write("-" * 155 + "\n")

        # Process each event
        for pe in processed_events:
            # Check if this is a split event
            if pe.get("is_split_event") and pe.get("split_info"):
                split_info = pe["split_info"]
                date_time = format_datetime(pe["transaction_time"])
                prev_position = split_info["prev_position"]
                new_position = split_info["new_position"]
                prev_avg_cost = split_info["prev_avg_cost"]
                new_avg_cost = split_info["new_avg_cost"]
                from_qty = split_info["from_qty"]
                to_qty = split_info["to_qty"]
                ratio = split_info["ratio"]
                cost_basis = split_info["cost_basis"]

                # Determine split type and format description
                # Calculate the actual split ratio (e.g., 2:1, 3:1, 1:2, etc.)
                # Find the greatest common divisor to simplify the ratio
                def gcd(a, b):
                    while b:
                        a, b = b, a % b
                    return a

                # Normalize to get the simplest ratio
                # For forward splits: from_qty shares become to_qty shares
                # (e.g., 1 share becomes 3 shares = 1:3)
                # For reverse splits: from_qty shares become to_qty shares
                # (e.g., 3 shares become 1 share = 3:1)
                if ratio < 1.0:
                    split_type = "REVERSE SPLIT"
                    # Reverse split: more shares become fewer shares
                    # Example: 25 shares -> 1.666667 shares = 15:1 reverse split
                    # Calculate as from_qty/to_qty to get the reverse ratio
                    if from_qty > 0 and to_qty > 0:
                        # Try to find a common multiplier to get integers
                        multiplier = 1
                        while (
                            from_qty * multiplier < 1000
                            and to_qty * multiplier < 1000
                            and abs(from_qty * multiplier - round(from_qty * multiplier)) > 0.001
                        ):
                            multiplier *= 10
                        from_int = int(round(from_qty * multiplier))
                        to_int = int(round(to_qty * multiplier))
                        if from_int > 0 and to_int > 0:
                            common = gcd(from_int, to_int)
                            from_int //= common
                            to_int //= common
                            split_desc = f"{from_int}:{to_int}"
                        else:
                            split_desc = f"{from_qty:.6f}:{to_qty:.6f}".rstrip("0").rstrip(".")
                    else:
                        split_desc = f"{from_qty:.6f}:{to_qty:.6f}".rstrip("0").rstrip(".")
                else:
                    split_type = "FORWARD SPLIT"
                    # Forward split: fewer shares become more shares
                    # Example: 0.1 shares -> 1 share = 1:10 forward split
                    if from_qty > 0 and to_qty > 0:
                        # Try to find a common multiplier to get integers
                        multiplier = 1
                        while (
                            from_qty * multiplier < 1000
                            and to_qty * multiplier < 1000
                            and abs(from_qty * multiplier - round(from_qty * multiplier)) > 0.001
                        ):
                            multiplier *= 10
                        from_int = int(round(from_qty * multiplier))
                        to_int = int(round(to_qty * multiplier))
                        if from_int > 0 and to_int > 0:
                            common = gcd(from_int, to_int)
                            from_int //= common
                            to_int //= common
                            split_desc = f"{from_int}:{to_int}"
                        else:
                            split_desc = f"{from_qty:.6f}:{to_qty:.6f}".rstrip("0").rstrip(".")
                    else:
                        split_desc = f"{from_qty:.6f}:{to_qty:.6f}".rstrip("0").rstrip(".")

                # Write split event line
                f.write("\n")
                f.write(">>>>>>>>>>> SPLIT EVENT OCCURRED ")
                f.write(f"Date: {date_time}, Type: {split_type} ({split_desc}), ")
                f.write(f"Ratio: {ratio:.6f}, ")
                f.write(
                    f"Position: {format_number(prev_position)} -> {format_number(new_position)}, "
                )
                avg_cost_change = (
                    f"Avg Cost: {format_currency(prev_avg_cost)} -> "
                    f"{format_currency(new_avg_cost)}, "
                )
                f.write(avg_cost_change)
                f.write(f"Cost Basis: {format_currency(cost_basis)} (unchanged)\n")
                f.write("\n")
                continue

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

            # Format accumulated gains (only show when it was updated,
            # i.e., when profit is calculated)
            accumulated_gains = pe.get("accumulated_gains", 0.0)
            if profit is not None:
                accumulated_gains_str = format_currency(accumulated_gains)
            else:
                accumulated_gains_str = "-"

            # Write row
            row = (
                f"{date_time:<20} {side:<10} {qty_str:<12} {price_str:<12} "
                f"{cost_basis_str:<15} {status_icon} {status:<9} {position_type:<6} "
                f"{position_str:<12} {avg_cost_str:<12} {profit_str:<15} "
                f"{accumulated_gains_str:<18}\n"
            )
            f.write(row)

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
    parser = argparse.ArgumentParser(
        description="Track balance/position for a specific symbol from analyzed trading events"
    )
    parser.add_argument(
        "symbol",
        type=str,
        help="Stock symbol to track (e.g., AAPL)",
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
        "--output",
        "-o",
        type=str,
        help="Path to output report file (overrides default)",
    )

    args = parser.parse_args()

    symbol = args.symbol
    # Get project root (four levels up from this file: src -> tax-report -> apps -> root)
    project_root = Path(__file__).parent.parent.parent.parent

    # Set default paths or use overrides
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

    if args.output:
        output_file = Path(args.output)
    else:
        # Default to reports subfolder in live directory
        reports_dir = project_root / "data" / "trading" / "alpaca" / "live" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_file = reports_dir / f"{symbol.upper()}_balance_report.txt"

    # Set splits file path
    splits_file = None
    if args.splits:
        splits_file = str(Path(args.splits))
    else:
        # Default splits file location (same directory as input)
        splits_file = str(input_file.parent / "splits.json")

    # Track balance
    try:
        processed_events = track_balance(symbol, str(input_file), splits_file)
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)

    if processed_events:
        # Generate report
        generate_report(symbol, processed_events, str(output_file))
        print(f"\nBalance tracking complete for {symbol.upper()}")
    else:
        print(f"No events found for symbol {symbol}")


if __name__ == "__main__":
    main()
