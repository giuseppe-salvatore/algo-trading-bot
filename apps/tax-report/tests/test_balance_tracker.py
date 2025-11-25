#!/usr/bin/env python3
"""
Tests for balance_tracker.py
"""

import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from balance_tracker import track_balance, generate_report


def create_test_events_file(events, filepath):
    """Helper to create a temporary events file."""
    with open(filepath, "w") as f:
        json.dump(events, f, indent=2)


def test_long_to_short_conversion():
    """Test that LONG->SHORT conversion splits into two events."""
    events = [
        {
            "id": "1",
            "symbol": "QQQ",
            "side": "buy",
            "qty": "5",
            "price": "100.00",
            "transaction_time": "2021-01-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "QQQ",
            "side": "sell",
            "qty": "10",  # Selling 10 when we only have 5
            "price": "110.00",
            "transaction_time": "2021-01-01T11:00:00Z",
            "order_id": "order2",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        processed = track_balance("QQQ", f.name)

        # Should have 3 events: open long, close long, open short
        assert len(processed) == 3, f"Expected 3 events, got {len(processed)}"

        # First event: open long
        assert processed[0]["status"] == "opened"
        assert processed[0]["position_after"] == 5.0
        assert processed[0]["profit"] is None

        # Second event: close long (split event)
        assert processed[1]["status"] == "closed"
        assert processed[1]["qty"] == 5.0  # Only the long portion
        assert processed[1]["position_after"] == 0.0
        assert processed[1]["profit"] is not None  # Should have profit

        # Third event: open short (split event)
        assert processed[2]["status"] == "opened"
        assert processed[2]["qty"] == 5.0  # Only the short portion
        assert processed[2]["side"] == "sell_short"
        assert processed[2]["position_after"] == -5.0
        assert processed[2]["profit"] is None

        Path(f.name).unlink()

    print("✓ test_long_to_short_conversion passed")


def test_short_to_long_conversion():
    """Test that SHORT->LONG conversion splits into two events."""
    events = [
        {
            "id": "1",
            "symbol": "QQQ",
            "side": "sell",
            "qty": "5",
            "price": "100.00",
            "transaction_time": "2021-01-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "QQQ",
            "side": "buy",
            "qty": "10",  # Buying 10 when we only have 5 short
            "price": "110.00",
            "transaction_time": "2021-01-01T11:00:00Z",
            "order_id": "order2",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        processed = track_balance("QQQ", f.name)

        # Should have 3 events: open short, close short, open long
        assert len(processed) == 3, f"Expected 3 events, got {len(processed)}"

        # First event: open short
        assert processed[0]["status"] == "opened"
        assert processed[0]["position_after"] == -5.0
        assert processed[0]["profit"] is None

        # Second event: close short (split event)
        assert processed[1]["status"] == "closed"
        assert processed[1]["qty"] == 5.0  # Only the short portion
        assert processed[1]["position_after"] == 0.0
        assert processed[1]["profit"] is not None  # Should have profit

        # Third event: open long (split event)
        assert processed[2]["status"] == "opened"
        assert processed[2]["qty"] == 5.0  # Only the long portion
        assert processed[2]["position_after"] == 5.0
        assert processed[2]["profit"] is None

        Path(f.name).unlink()

    print("✓ test_short_to_long_conversion passed")


def test_quantity_verification():
    """Test that quantities add up correctly across events."""
    events = [
        {
            "id": "1",
            "symbol": "QQQ",
            "side": "buy",
            "qty": "20",  # Total should be 20
            "price": "100.00",
            "transaction_time": "2021-01-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "QQQ",
            "side": "sell",
            "qty": "5",
            "price": "110.00",
            "transaction_time": "2021-01-01T11:00:00Z",
            "order_id": "order2",
        },
        {
            "id": "3",
            "symbol": "QQQ",
            "side": "sell",
            "qty": "15",
            "price": "120.00",
            "transaction_time": "2021-01-01T12:00:00Z",
            "order_id": "order3",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        processed = track_balance("QQQ", f.name)

        # Verify quantities
        total_bought = sum(e["qty"] for e in processed if e["side"] == "buy")
        total_sold = sum(e["qty"] for e in processed if e["side"] in ["sell", "sell_short"])

        # Should have bought 20 and sold 20 (5 + 15)
        assert total_bought == 20.0, f"Expected 20 shares bought, got {total_bought}"
        assert total_sold == 20.0, f"Expected 20 shares sold, got {total_sold}"

        # Final position should be 0
        assert processed[-1]["position_after"] == 0.0

        Path(f.name).unlink()

    print("✓ test_quantity_verification passed")


def test_cum_qty_handling():
    """Test that cum_qty from analyze_events is correctly used."""
    # Simulate what analyze_events produces: single event with cum_qty as qty
    events = [
        {
            "id": "1",
            "symbol": "QQQ",
            "side": "buy",
            "qty": "20",  # This should be the total from cum_qty
            "price": "100.00",
            "transaction_time": "2021-01-01T10:00:00Z",
            "order_id": "order1",
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        processed = track_balance("QQQ", f.name)

        # Should have 1 event with qty=20
        assert len(processed) == 1
        assert processed[0]["qty"] == 20.0
        assert processed[0]["position_after"] == 20.0

        Path(f.name).unlink()

    print("✓ test_cum_qty_handling passed")


if __name__ == "__main__":
    print("Running tests for balance_tracker.py...\n")
    test_long_to_short_conversion()
    test_short_to_long_conversion()
    test_quantity_verification()
    test_cum_qty_handling()
    print("\n✅ All tests passed!")
