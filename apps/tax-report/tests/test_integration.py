#!/usr/bin/env python3
"""
Integration tests for the full tax-report pipeline.
Tests that events flow correctly from taxable_activities.json -> analyzed -> balance report.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyze_events import analyze_events
from balance_tracker import track_balance


def test_full_pipeline_with_partial_fills():
    """Test the full pipeline with partial fills that should be reconciled."""
    # Simulate the actual bug case: 4 events with same order_id
    raw_events = [
        {
            "id": "1",
            "activity_type": "FILL",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "type": "partial_fill",
            "price": "318.03",
            "qty": "8",
            "side": "buy",
            "symbol": "QQQ",
            "leaves_qty": "12",
            "order_id": "f886f6b0-0ef7-469f-8ab6-24cdabed3b48",
            "cum_qty": "8",
            "order_status": "partially_filled",
        },
        {
            "id": "2",
            "activity_type": "FILL",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "type": "partial_fill",
            "price": "318.03",
            "qty": "1",
            "side": "buy",
            "symbol": "QQQ",
            "leaves_qty": "11",
            "order_id": "f886f6b0-0ef7-469f-8ab6-24cdabed3b48",
            "cum_qty": "9",
            "order_status": "partially_filled",
        },
        {
            "id": "3",
            "activity_type": "FILL",
            "transaction_time": "2021-03-17T13:59:29.684Z",
            "type": "partial_fill",
            "price": "318.03",
            "qty": "2",
            "side": "buy",
            "symbol": "QQQ",
            "leaves_qty": "9",
            "order_id": "f886f6b0-0ef7-469f-8ab6-24cdabed3b48",
            "cum_qty": "11",
            "order_status": "partially_filled",
        },
        {
            "id": "4",
            "activity_type": "FILL",
            "transaction_time": "2021-03-17T13:59:29.685Z",
            "type": "fill",
            "price": "318.03",
            "qty": "9",
            "side": "buy",
            "symbol": "QQQ",
            "leaves_qty": "0",
            "order_id": "f886f6b0-0ef7-469f-8ab6-24cdabed3b48",
            "cum_qty": "20",
            "order_status": "filled",
        },
    ]

    # Step 1: Analyze events (should reconcile to 1 event with qty=20)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(raw_events, f, indent=2)
        temp_input = f.name

    try:
        analyzed_events = analyze_events(temp_input)

        # Should have 1 event (reconciled)
        assert len(analyzed_events) == 1, f"Expected 1 analyzed event, got {len(analyzed_events)}"

        # Should have qty=20 (from cum_qty)
        analyzed_event = analyzed_events[0]
        assert float(analyzed_event["qty"]) == 20.0, (
            f"Expected qty=20.0, got {analyzed_event['qty']}"
        )
        assert float(analyzed_event["cum_qty"]) == 20.0

        # Step 2: Track balance (should show 20 shares)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump(analyzed_events, f2, indent=2)
            temp_analyzed = f2.name

        try:
            processed = track_balance("QQQ", temp_analyzed)

            # Should have 1 event with 20 shares
            assert len(processed) == 1
            assert processed[0]["qty"] == 20.0
            assert processed[0]["position_after"] == 20.0
            assert processed[0]["status"] == "opened"

            print("✓ test_full_pipeline_with_partial_fills passed")
        finally:
            Path(temp_analyzed).unlink()
    finally:
        Path(temp_input).unlink()


def test_quantity_consistency_check():
    """Test that we can verify quantities are consistent across the pipeline."""
    # Create events that should add up correctly
    raw_events = [
        {
            "id": "1",
            "order_id": "order1",
            "transaction_time": "2021-01-01T10:00:00Z",
            "type": "fill",
            "price": "100.00",
            "qty": "10",
            "side": "buy",
            "symbol": "QQQ",
            "cum_qty": "10",
            "order_status": "filled",
        },
        {
            "id": "2",
            "order_id": "order2",
            "transaction_time": "2021-01-01T11:00:00Z",
            "type": "fill",
            "price": "110.00",
            "qty": "5",
            "side": "sell",
            "symbol": "QQQ",
            "cum_qty": "5",
            "order_status": "filled",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(raw_events, f, indent=2)
        temp_input = f.name

    try:
        analyzed_events = analyze_events(temp_input)

        # Calculate total quantities
        total_bought = sum(float(e["qty"]) for e in analyzed_events if e["side"] == "buy")
        total_sold = sum(float(e["qty"]) for e in analyzed_events if e["side"] == "sell")

        assert total_bought == 10.0
        assert total_sold == 5.0

        # Track balance
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump(analyzed_events, f2, indent=2)
            temp_analyzed = f2.name

        try:
            processed = track_balance("QQQ", temp_analyzed)

            # Verify quantities in processed events match
            processed_bought = sum(e["qty"] for e in processed if e["side"] == "buy")
            processed_sold = sum(e["qty"] for e in processed if e["side"] in ["sell", "sell_short"])

            assert processed_bought == total_bought, (
                "Quantities should match between analyzed and processed"
            )
            assert processed_sold == total_sold, (
                "Quantities should match between analyzed and processed"
            )

            print("✓ test_quantity_consistency_check passed")
        finally:
            Path(temp_analyzed).unlink()
    finally:
        Path(temp_input).unlink()


if __name__ == "__main__":
    print("Running integration tests...\n")
    test_full_pipeline_with_partial_fills()
    test_quantity_consistency_check()
    print("\n✅ All integration tests passed!")
