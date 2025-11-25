#!/usr/bin/env python3
"""
Tests for analyze_events.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyze_events import reconcile_events, is_partial_fill


def test_reconcile_same_price_with_partial_fills():
    """Test that partial fills are correctly reconciled when prices are the same."""
    # This is the bug case: 4 events with same price, should use cum_qty from fill event
    events = [
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "side": "buy",
            "qty": "8",
            "price": "318.03",
            "type": "partial_fill",
            "cum_qty": "8",
            "order_status": "partially_filled",
            "symbol": "QQQ",
        },
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "side": "buy",
            "qty": "1",
            "price": "318.03",
            "type": "partial_fill",
            "cum_qty": "9",
            "order_status": "partially_filled",
            "symbol": "QQQ",
        },
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "side": "buy",
            "qty": "2",
            "price": "318.03",
            "type": "partial_fill",
            "cum_qty": "11",
            "order_status": "partially_filled",
            "symbol": "QQQ",
        },
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.685Z",
            "side": "buy",
            "qty": "9",  # This is just the last increment, not total
            "price": "318.03",
            "type": "fill",
            "cum_qty": "20",  # This is the total!
            "order_status": "filled",
            "symbol": "QQQ",
        },
    ]

    result = reconcile_events(events)

    # Should use cum_qty (20) as the qty, not the individual qty (9)
    assert float(result["qty"]) == 20.0, f"Expected qty=20.0, got {result['qty']}"
    assert float(result["cum_qty"]) == 20.0, f"Expected cum_qty=20.0, got {result['cum_qty']}"
    assert result["price"] == "318.03"
    assert result["type"] == "fill"
    assert result["order_status"] == "filled"
    print("✓ test_reconcile_same_price_with_partial_fills passed")


def test_reconcile_different_prices():
    """Test reconciliation when prices differ (weighted average)."""
    events = [
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "side": "buy",
            "qty": "10",
            "price": "100.00",
            "type": "partial_fill",
            "cum_qty": "10",
            "order_status": "partially_filled",
            "symbol": "QQQ",
        },
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.685Z",
            "side": "buy",
            "qty": "10",
            "price": "110.00",
            "type": "fill",
            "cum_qty": "20",
            "order_status": "filled",
            "symbol": "QQQ",
        },
    ]

    result = reconcile_events(events)

    # Weighted average: (10*100 + 10*110) / 20 = 105.00
    assert float(result["qty"]) == 20.0
    assert float(result["cum_qty"]) == 20.0
    assert float(result["price"]) == 105.0
    assert result["type"] == "fill"
    print("✓ test_reconcile_different_prices passed")


def test_reconcile_single_event():
    """Test that single events are returned as-is."""
    events = [
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "side": "buy",
            "qty": "10",
            "price": "100.00",
            "type": "fill",
            "cum_qty": "10",
            "order_status": "filled",
            "symbol": "QQQ",
        }
    ]

    result = reconcile_events(events)

    assert result == events[0]
    print("✓ test_reconcile_single_event passed")


def test_is_partial_fill():
    """Test partial fill detection."""
    partial_fill_event = {"type": "partial_fill", "order_status": "filled"}
    assert is_partial_fill(partial_fill_event) == True

    partial_fill_event2 = {"type": "fill", "order_status": "partially_filled"}
    assert is_partial_fill(partial_fill_event2) == True

    fill_event = {"type": "fill", "order_status": "filled"}
    assert is_partial_fill(fill_event) == False

    print("✓ test_is_partial_fill passed")


def test_reconcile_no_fill_event():
    """Test reconciliation when there's no fill event (should use last event's cum_qty)."""
    events = [
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "side": "buy",
            "qty": "10",
            "price": "100.00",
            "type": "partial_fill",
            "cum_qty": "10",
            "order_status": "partially_filled",
            "symbol": "QQQ",
        },
        {
            "order_id": "test-order",
            "transaction_time": "2021-03-17T13:59:29.685Z",
            "side": "buy",
            "qty": "10",
            "price": "100.00",
            "type": "partial_fill",
            "cum_qty": "20",
            "order_status": "partially_filled",
            "symbol": "QQQ",
        },
    ]

    result = reconcile_events(events)

    # Should use last event's cum_qty
    assert float(result["qty"]) == 20.0
    assert float(result["cum_qty"]) == 20.0
    assert result["type"] == "fill"
    assert result["order_status"] == "filled"
    print("✓ test_reconcile_no_fill_event passed")


if __name__ == "__main__":
    print("Running tests for analyze_events.py...\n")
    test_reconcile_same_price_with_partial_fills()
    test_reconcile_different_prices()
    test_reconcile_single_event()
    test_is_partial_fill()
    test_reconcile_no_fill_event()
    print("\n✅ All tests passed!")
