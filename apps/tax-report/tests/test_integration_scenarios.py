#!/usr/bin/env python3
"""
Integration tests for the full tax-report pipeline using test data.
Tests that events flow correctly from test data -> analyzed -> balance report.
Each test scenario targets a specific edge case or scenario.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyze_events import analyze_events
from balance_tracker import track_balance


def get_test_data_path(filename):
    """Get path to test data file."""
    # Get project root (four levels up from this file: tests -> tax-report -> apps -> root)
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "data" / "trading" / "alpaca" / "test" / filename


def test_scenario_pos_open():
    """Integration test for TEST_POS_OPEN: Position remains open at end."""
    test_input = str(get_test_data_path("taxable_activities.json"))
    analyzed_events = analyze_events(test_input)

    # Filter for TEST_POS_OPEN
    test_events = [e for e in analyzed_events if e.get("symbol") == "TEST_POS_OPEN"]
    assert len(test_events) > 0, "Should have events for TEST_POS_OPEN"

    # Write to temp file for balance tracking
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_analyzed = f.name

    try:
        processed = track_balance("TEST_POS_OPEN", temp_analyzed)

        # Verify position is open
        assert len(processed) > 0
        assert processed[-1]["position_after"] == 8.0  # 10 + 5 - 7
        assert processed[-1]["status"] != "closed"

        print("✓ test_scenario_pos_open passed")
    finally:
        Path(temp_analyzed).unlink()


def test_scenario_forward_split():
    """Integration test for TEST_FW_SPLIT: Forward split with position closure."""
    test_input = str(get_test_data_path("taxable_activities.json"))
    test_splits = str(get_test_data_path("splits.json"))

    analyzed_events = analyze_events(test_input)

    # Filter for TEST_FW_SPLIT
    test_events = [e for e in analyzed_events if e.get("symbol") == "TEST_FW_SPLIT"]
    assert len(test_events) > 0, "Should have events for TEST_FW_SPLIT"

    # Write to temp file for balance tracking
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_analyzed = f.name

    try:
        processed = track_balance("TEST_FW_SPLIT", temp_analyzed, test_splits)

        # Verify position is closed after split
        assert len(processed) > 0
        assert processed[-1]["position_after"] == 0.0
        assert processed[-1]["status"] == "closed"

        # Verify split was applied (should have a split event)
        split_events = [e for e in processed if e.get("is_split_event") and e.get("split_info")]
        assert len(split_events) > 0, "Should have split event"

        print("✓ test_scenario_forward_split passed")
    finally:
        Path(temp_analyzed).unlink()


def test_scenario_backward_split():
    """Integration test for TEST_BW_SPLIT: Backward split with position closure."""
    test_input = str(get_test_data_path("taxable_activities.json"))
    test_splits = str(get_test_data_path("splits.json"))

    analyzed_events = analyze_events(test_input)

    # Filter for TEST_BW_SPLIT
    test_events = [e for e in analyzed_events if e.get("symbol") == "TEST_BW_SPLIT"]
    assert len(test_events) > 0, "Should have events for TEST_BW_SPLIT"

    # Write to temp file for balance tracking
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_analyzed = f.name

    try:
        processed = track_balance("TEST_BW_SPLIT", temp_analyzed, test_splits)

        # Verify position is closed after split
        assert len(processed) > 0
        assert processed[-1]["position_after"] == 0.0
        assert processed[-1]["status"] == "closed"

        # Verify split was applied
        split_events = [e for e in processed if e.get("is_split_event") and e.get("split_info")]
        assert len(split_events) > 0, "Should have split event"

        print("✓ test_scenario_backward_split passed")
    finally:
        Path(temp_analyzed).unlink()


def test_scenario_short_only():
    """Integration test for TEST_SHORT: Short-only positions."""
    test_input = str(get_test_data_path("taxable_activities.json"))
    analyzed_events = analyze_events(test_input)

    # Filter for TEST_SHORT
    test_events = [e for e in analyzed_events if e.get("symbol") == "TEST_SHORT"]
    assert len(test_events) > 0, "Should have events for TEST_SHORT"

    # Write to temp file for balance tracking
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_analyzed = f.name

    try:
        processed = track_balance("TEST_SHORT", temp_analyzed)

        # Verify position is closed
        assert len(processed) > 0
        assert processed[-1]["position_after"] == 0.0
        assert processed[-1]["status"] == "closed"

        # First event should be a short position
        assert processed[0]["position_after"] < 0

        print("✓ test_scenario_short_only passed")
    finally:
        Path(temp_analyzed).unlink()


def test_scenario_partial_fill():
    """Integration test for TEST_PARTIAL_FILL: Partial fill reconciliation."""
    test_input = str(get_test_data_path("taxable_activities.json"))
    analyzed_events = analyze_events(test_input)

    # Filter for TEST_PARTIAL_FILL
    test_events = [e for e in analyzed_events if e.get("symbol") == "TEST_PARTIAL_FILL"]
    assert len(test_events) > 0, "Should have events for TEST_PARTIAL_FILL"

    # Verify partial fills were reconciled
    # Should have fewer events than raw data (partial fills merged)
    # Check that cum_qty is used correctly

    # Write to temp file for balance tracking
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_analyzed = f.name

    try:
        processed = track_balance("TEST_PARTIAL_FILL", temp_analyzed)

        # Should process events successfully
        assert len(processed) > 0

        # Position should be closed (bought 20, sold 20)
        assert processed[-1]["position_after"] == 0.0

        print("✓ test_scenario_partial_fill passed")
    finally:
        Path(temp_analyzed).unlink()


def test_scenario_reverse_long():
    """Integration test for TEST_REVERSE_LONG: Long-to-short reversal."""
    test_input = str(get_test_data_path("taxable_activities.json"))
    analyzed_events = analyze_events(test_input)

    # Filter for TEST_REVERSE_LONG
    test_events = [e for e in analyzed_events if e.get("symbol") == "TEST_REVERSE_LONG"]
    assert len(test_events) > 0, "Should have events for TEST_REVERSE_LONG"

    # Write to temp file for balance tracking
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_analyzed = f.name

    try:
        processed = track_balance("TEST_REVERSE_LONG", temp_analyzed)

        # Should have split events (close long, open short)
        assert len(processed) >= 3

        # Final position should be short
        assert processed[-1]["position_after"] < 0
        assert processed[-1]["side"] == "sell_short"

        # Should have closed long position first
        closed_events = [
            e for e in processed if e.get("status") == "closed" and e.get("prev_position", 0) > 0
        ]
        assert len(closed_events) > 0

        print("✓ test_scenario_reverse_long passed")
    finally:
        Path(temp_analyzed).unlink()


def test_scenario_reverse_short():
    """Integration test for TEST_REVERSE_SHORT: Short-to-long reversal."""
    test_input = str(get_test_data_path("taxable_activities.json"))
    analyzed_events = analyze_events(test_input)

    # Filter for TEST_REVERSE_SHORT
    test_events = [e for e in analyzed_events if e.get("symbol") == "TEST_REVERSE_SHORT"]
    assert len(test_events) > 0, "Should have events for TEST_REVERSE_SHORT"

    # Write to temp file for balance tracking
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_analyzed = f.name

    try:
        processed = track_balance("TEST_REVERSE_SHORT", temp_analyzed)

        # Should have split events (close short, open long)
        assert len(processed) >= 3

        # Final position should be long
        assert processed[-1]["position_after"] > 0

        # Should have closed short position first
        closed_events = [
            e for e in processed if e.get("status") == "closed" and e.get("prev_position", 0) < 0
        ]
        assert len(closed_events) > 0

        print("✓ test_scenario_reverse_short passed")
    finally:
        Path(temp_analyzed).unlink()


if __name__ == "__main__":
    print("Running integration scenario tests...\n")
    test_scenario_pos_open()
    test_scenario_forward_split()
    test_scenario_backward_split()
    test_scenario_short_only()
    test_scenario_partial_fill()
    test_scenario_reverse_long()
    test_scenario_reverse_short()
    print("\n✅ All integration scenario tests passed!")
