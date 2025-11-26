#!/usr/bin/env python3
"""
Tests for balance_tracker.py
"""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from balance_tracker import track_balance


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

        processed, _, _ = track_balance("QQQ", f.name)

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

        processed, _, _ = track_balance("QQQ", f.name)

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

        processed, _, _ = track_balance("QQQ", f.name)

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

        processed, _, _ = track_balance("QQQ", f.name)

        # Should have 1 event with qty=20
        assert len(processed) == 1
        assert processed[0]["qty"] == 20.0
        assert processed[0]["position_after"] == 20.0

        Path(f.name).unlink()

    print("✓ test_cum_qty_handling passed")


def test_pos_open():
    """Test scenario: Position remains open at end (TEST_POS_OPEN)."""
    events = [
        {
            "id": "1",
            "symbol": "TEST_POS_OPEN",
            "side": "buy",
            "qty": "10",
            "price": "100.00",
            "transaction_time": "2024-01-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "TEST_POS_OPEN",
            "side": "buy",
            "qty": "5",
            "price": "110.00",
            "transaction_time": "2024-01-01T11:00:00Z",
            "order_id": "order2",
        },
        {
            "id": "3",
            "symbol": "TEST_POS_OPEN",
            "side": "sell",
            "qty": "7",
            "price": "120.00",
            "transaction_time": "2024-01-01T12:00:00Z",
            "order_id": "order3",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        processed, _, _ = track_balance("TEST_POS_OPEN", f.name)

        # Should have 3 events
        assert len(processed) == 3

        # Final position should be 8 (10 + 5 - 7)
        assert processed[-1]["position_after"] == 8.0
        assert processed[-1]["status"] != "closed"  # Position should still be open

        Path(f.name).unlink()

    print("✓ test_pos_open passed")


def test_forward_split():
    """Test scenario: Forward split handling and position closure (TEST_FW_SPLIT)."""
    events = [
        {
            "id": "1",
            "symbol": "TEST_FW_SPLIT",
            "side": "buy",
            "qty": "10",
            "price": "100.00",
            "transaction_time": "2024-02-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "TEST_FW_SPLIT",
            "side": "sell",
            "qty": "30",
            "price": "35.00",
            "transaction_time": "2024-02-02T12:00:00Z",
            "order_id": "order2",
        },
    ]

    splits = [
        {
            "id": "split-remove",
            "activity_type": "SPLIT",
            "date": "2024-02-02",
            "created_at": "2024-02-02T11:00:00Z",
            "net_amount": "0",
            "description": "REMOVE, From QTY:10, To QTY:30, Position Value:1000.00",
            "symbol": "TEST_FW_SPLIT",
            "qty": "-10",
            "price": "100.00",
            "status": "executed",
        },
        {
            "id": "split-add",
            "activity_type": "SPLIT",
            "date": "2024-02-02",
            "created_at": "2024-02-02T11:00:01Z",
            "net_amount": "0",
            "description": "ADD, From QTY:10, To QTY:30, Position Value:1000.00",
            "symbol": "TEST_FW_SPLIT",
            "qty": "30",
            "price": "33.33",
            "status": "executed",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as s:
            create_test_events_file(splits, s.name)

            processed, _, _ = track_balance("TEST_FW_SPLIT", f.name, s.name)

            # Should have split event + 2 trading events (or 3 if split creates separate event)
            assert len(processed) >= 2

            # Final position should be 0 (closed)
            assert processed[-1]["position_after"] == 0.0
            assert processed[-1]["status"] == "closed"

            Path(f.name).unlink()
            Path(s.name).unlink()

    print("✓ test_forward_split passed")


def test_backward_split():
    """Test scenario: Backward split handling and position closure (TEST_BW_SPLIT)."""
    events = [
        {
            "id": "1",
            "symbol": "TEST_BW_SPLIT",
            "side": "buy",
            "qty": "30",
            "price": "100.00",
            "transaction_time": "2024-03-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "TEST_BW_SPLIT",
            "side": "sell",
            "qty": "10",
            "price": "300.00",
            "transaction_time": "2024-03-02T12:00:00Z",
            "order_id": "order2",
        },
    ]

    splits = [
        {
            "id": "split-remove",
            "activity_type": "SPLIT",
            "activity_sub_type": "RSPLIT",
            "date": "2024-03-02",
            "created_at": "2024-03-02T11:00:00Z",
            "net_amount": "0",
            "description": "REMOVE, From QTY:30, To QTY:10, Position Value:3000.00",
            "symbol": "TEST_BW_SPLIT",
            "qty": "-30",
            "price": "100.00",
            "status": "executed",
        },
        {
            "id": "split-add",
            "activity_type": "SPLIT",
            "activity_sub_type": "RSPLIT",
            "date": "2024-03-02",
            "created_at": "2024-03-02T11:00:01Z",
            "net_amount": "0",
            "description": "ADD, From QTY:30, To QTY:10, Position Value:3000.00",
            "symbol": "TEST_BW_SPLIT",
            "qty": "10",
            "price": "300.00",
            "status": "executed",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as s:
            create_test_events_file(splits, s.name)

            processed, _, _ = track_balance("TEST_BW_SPLIT", f.name, s.name)

            # Should have split event + 2 trading events
            assert len(processed) >= 2

            # Final position should be 0 (closed)
            assert processed[-1]["position_after"] == 0.0
            assert processed[-1]["status"] == "closed"

            Path(f.name).unlink()
            Path(s.name).unlink()

    print("✓ test_backward_split passed")


def test_short_only():
    """Test scenario: Short-only positions (TEST_SHORT)."""
    events = [
        {
            "id": "1",
            "symbol": "TEST_SHORT",
            "side": "sell",
            "qty": "10",
            "price": "100.00",
            "transaction_time": "2024-04-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "TEST_SHORT",
            "side": "sell",
            "qty": "5",
            "price": "110.00",
            "transaction_time": "2024-04-01T11:00:00Z",
            "order_id": "order2",
        },
        {
            "id": "3",
            "symbol": "TEST_SHORT",
            "side": "buy",
            "qty": "15",
            "price": "90.00",
            "transaction_time": "2024-04-01T12:00:00Z",
            "order_id": "order3",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        processed, _, _ = track_balance("TEST_SHORT", f.name)

        # Should have 3 events
        assert len(processed) == 3

        # Final position should be 0 (closed)
        assert processed[-1]["position_after"] == 0.0
        assert processed[-1]["status"] == "closed"

        # First two events should open/update short positions
        assert processed[0]["position_after"] < 0  # Short position
        assert processed[1]["position_after"] < 0  # Still short

        Path(f.name).unlink()

    print("✓ test_short_only passed")


def test_reverse_long():
    """Test scenario: Long-to-short reversal (TEST_REVERSE_LONG)."""
    events = [
        {
            "id": "1",
            "symbol": "TEST_REVERSE_LONG",
            "side": "buy",
            "qty": "5",
            "price": "100.00",
            "transaction_time": "2024-06-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "TEST_REVERSE_LONG",
            "side": "sell",
            "qty": "10",
            "price": "110.00",
            "transaction_time": "2024-06-01T11:00:00Z",
            "order_id": "order2",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        processed, _, _ = track_balance("TEST_REVERSE_LONG", f.name)

        # Should have 3 events: open long, close long, open short
        assert len(processed) == 3

        # First event: open long
        assert processed[0]["status"] == "opened"
        assert processed[0]["position_after"] == 5.0

        # Second event: close long
        assert processed[1]["status"] == "closed"
        assert processed[1]["position_after"] == 0.0

        # Third event: open short
        assert processed[2]["status"] == "opened"
        assert processed[2]["side"] == "sell_short"
        assert processed[2]["position_after"] == -5.0

        Path(f.name).unlink()

    print("✓ test_reverse_long passed")


def test_reverse_short():
    """Test scenario: Short-to-long reversal (TEST_REVERSE_SHORT)."""
    events = [
        {
            "id": "1",
            "symbol": "TEST_REVERSE_SHORT",
            "side": "sell",
            "qty": "5",
            "price": "100.00",
            "transaction_time": "2024-07-01T10:00:00Z",
            "order_id": "order1",
        },
        {
            "id": "2",
            "symbol": "TEST_REVERSE_SHORT",
            "side": "buy",
            "qty": "10",
            "price": "90.00",
            "transaction_time": "2024-07-01T11:00:00Z",
            "order_id": "order2",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        processed, _, _ = track_balance("TEST_REVERSE_SHORT", f.name)

        # Should have 3 events: open short, close short, open long
        assert len(processed) == 3

        # First event: open short
        assert processed[0]["status"] == "opened"
        assert processed[0]["position_after"] == -5.0

        # Second event: close short
        assert processed[1]["status"] == "closed"
        assert processed[1]["position_after"] == 0.0

        # Third event: open long
        assert processed[2]["status"] == "opened"
        assert processed[2]["position_after"] == 5.0

        Path(f.name).unlink()

    print("✓ test_reverse_short passed")


def test_symbol_name_change():
    """Test symbol name change handling (TEST_SYM_CNG -> TEST_SYM_CNG1)."""
    # Test with old symbol name (TEST_SYM_CNG)
    events = [
        {
            "id": "20240801100000001::test-sym-cng-1",
            "symbol": "TEST_SYM_CNG",
            "side": "buy",
            "qty": "10",
            "price": "100.00",
            "transaction_time": "2024-08-01T10:00:00Z",
            "order_id": "order-sym-cng-1",
        },
        {
            "id": "20240801120000002::test-sym-cng1-1",
            "symbol": "TEST_SYM_CNG1",
            "side": "sell",
            "qty": "10",
            "price": "110.00",
            "transaction_time": "2024-08-01T12:00:00Z",
            "order_id": "order-sym-cng1-1",
        },
    ]

    name_changes = [
        {
            "id": "20240801110000000::test-name-change-1",
            "activity_type": "NC",
            "activity_sub_type": "SNC",
            "date": "2024-08-01",
            "created_at": "2024-08-01T11:00:00Z",
            "net_amount": "0",
            "description": "Name Change from TEST_SYM_CNG to TEST_SYM_CNG1",
            "symbol": "TEST_SYM_CNG1",
            "qty": "10",
            "price": "100.00",
            "status": "executed",
        },
        {
            "id": "20240801110000001::test-name-change-2",
            "activity_type": "NC",
            "activity_sub_type": "SNC",
            "date": "2024-08-01",
            "created_at": "2024-08-01T11:00:01Z",
            "net_amount": "0",
            "description": "Name Change from TEST_SYM_CNG to TEST_SYM_CNG1",
            "symbol": "TEST_SYM_CNG",
            "qty": "-10",
            "price": "100.00",
            "status": "executed",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        create_test_events_file(events, f.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as n:
            create_test_events_file(name_changes, n.name)

            # Test with old symbol name
            processed, latest_symbol, name_change_history = track_balance(
                "TEST_SYM_CNG", f.name, None, n.name
            )

            # Should have 2 events (buy and sell)
            assert len(processed) == 2, f"Expected 2 events, got {len(processed)}"

            # Latest symbol should be TEST_SYM_CNG1
            assert latest_symbol == "TEST_SYM_CNG1", (
                f"Expected latest symbol TEST_SYM_CNG1, got {latest_symbol}"
            )

            # Should have name change history
            assert len(name_change_history) == 1, (
                f"Expected 1 name change, got {len(name_change_history)}"
            )
            assert name_change_history[0]["from"] == "TEST_SYM_CNG"
            assert name_change_history[0]["to"] == "TEST_SYM_CNG1"

            # First event: buy with old symbol (normalized to new)
            assert processed[0]["side"] == "buy"
            assert processed[0]["qty"] == 10.0
            assert processed[0]["position_after"] == 10.0
            assert processed[0]["status"] == "opened"

            # Second event: sell with new symbol
            assert processed[1]["side"] == "sell"
            assert processed[1]["qty"] == 10.0
            assert processed[1]["position_after"] == 0.0
            assert processed[1]["status"] == "closed"
            assert processed[1]["profit"] is not None
            assert processed[1]["profit"] == 100.0  # (110 - 100) * 10

            # Test with new symbol name (should work the same)
            processed2, latest_symbol2, name_change_history2 = track_balance(
                "TEST_SYM_CNG1", f.name, None, n.name
            )

            # Should have same results
            assert len(processed2) == 2
            assert latest_symbol2 == "TEST_SYM_CNG1"
            assert len(name_change_history2) == 1

            Path(f.name).unlink()
            Path(n.name).unlink()

    print("✓ test_symbol_name_change passed")


if __name__ == "__main__":
    print("Running tests for balance_tracker.py...\n")
    test_long_to_short_conversion()
    test_short_to_long_conversion()
    test_quantity_verification()
    test_cum_qty_handling()
    test_pos_open()
    test_forward_split()
    test_backward_split()
    test_short_only()
    test_reverse_long()
    test_reverse_short()
    test_symbol_name_change()
    print("\n✅ All tests passed!")
