#!/usr/bin/env python3
"""
Script to combine events with the same order_id from taxable_activities.json.
- If prices are the same, removes partial fill events and keeps fill events
- If prices differ or transaction times differ (at second resolution), prints warnings
- Creates a new combined JSON file
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


def truncate_to_seconds(iso_timestamp: str) -> str:
    """Truncate ISO timestamp to second resolution."""
    try:
        # Parse the timestamp
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        # Truncate to seconds
        dt_truncated = dt.replace(microsecond=0)
        # Return in ISO format
        return dt_truncated.isoformat().replace('+00:00', 'Z')
    except Exception as e:
        print(f"Warning: Could not parse timestamp {iso_timestamp}: {e}")
        return iso_timestamp


def is_partial_fill(event: Dict[str, Any]) -> bool:
    """Check if an event is a partial fill."""
    return (event.get("type") == "partial_fill" or 
            event.get("order_status") == "partially_filled")


def combine_events(input_file: str, output_file: str):
    """Combine events with the same order_id."""
    # Load the JSON file
    print(f"Loading events from {input_file}...")
    with open(input_file, 'r') as f:
        events = json.load(f)
    
    print(f"Loaded {len(events)} events")
    
    # Group events by order_id
    events_by_order_id = defaultdict(list)
    for event in events:
        order_id = event.get("order_id")
        if order_id:
            events_by_order_id[order_id].append(event)
    
    print(f"Found {len(events_by_order_id)} unique order IDs")
    
    # Process each group
    combined_events = []
    warnings = []
    
    for order_id, order_events in events_by_order_id.items():
        if len(order_events) == 1:
            # Single event, just add it
            combined_events.append(order_events[0])
        else:
            # Multiple events with same order_id
            # Separate partial fills and full fills
            partial_fills = [e for e in order_events if is_partial_fill(e)]
            full_fills = [e for e in order_events if not is_partial_fill(e)]
            
            # Check prices
            prices = [float(e.get("price", 0)) for e in order_events]
            prices_set = set(prices)
            
            # Check transaction times at second resolution
            transaction_times = [truncate_to_seconds(e.get("transaction_time", "")) 
                               for e in order_events]
            times_set = set(transaction_times)
            
            # Check for warnings
            if len(prices_set) > 1:
                warning = (f"WARNING: Order ID {order_id} has different prices: "
                          f"{sorted(prices_set)}")
                warnings.append(warning)
                print(warning)
            
            if len(times_set) > 1:
                warning = (f"WARNING: Order ID {order_id} has different transaction times "
                          f"(at second resolution): {sorted(times_set)}")
                warnings.append(warning)
                print(warning)
            
            # If prices are the same, remove partial fills and keep full fills
            if len(prices_set) == 1:
                if full_fills:
                    # Keep only full fills
                    combined_events.extend(full_fills)
                else:
                    # No full fills, keep all events (shouldn't happen normally)
                    combined_events.extend(order_events)
            else:
                # Prices differ, keep all events but we've already warned
                combined_events.extend(order_events)
    
    # Sort combined events by transaction_time (maintain original order if possible)
    combined_events.sort(key=lambda x: x.get("transaction_time", ""))
    
    # Save to output file
    print(f"\nWriting {len(combined_events)} combined events to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(combined_events, f, indent=4)
    
    print(f"Done! Created {output_file}")
    if warnings:
        print(f"\nTotal warnings: {len(warnings)}")
    else:
        print("\nNo warnings generated.")


def main():
    """Main entry point for combine_events script."""
    # Get project root (four levels up from this file: src -> tax-report -> apps -> root)
    project_root = Path(__file__).parent.parent.parent.parent
    input_file = project_root / "data" / "taxable_activities.json"
    output_file = project_root / "data" / "taxable_activities_combined.json"
    
    combine_events(str(input_file), str(output_file))


if __name__ == "__main__":
    main()


