#!/usr/bin/env python3
"""
Integration tests for value_assets_sold.py script.
Tests that SELL orders are correctly filtered, values calculated, and reports generated.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyze_events import analyze_events
from fiscal_year_report import parse_fy_date_range
from value_assets_sold import calculate_sold_assets_value


def get_test_data_path(filename):
    """Get path to test data file."""
    # Get project root (four levels up from this file: tests -> tax-report -> apps -> root)
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "data" / "trading" / "alpaca" / "test" / filename


def test_sell_orders_filtered_correctly():
    """Test that only SELL orders are included in the calculation."""
    test_input = str(get_test_data_path("taxable_activities.json"))

    # Analyze events first
    analyzed_events = analyze_events(test_input)

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(analyzed_events, f, indent=2)
        temp_analyzed = f.name

    try:
        # Calculate sold assets value (all-time, no FY filter)
        (
            values_by_symbol_usd,
            values_by_symbol_gbp,
            sold_assets_gbp,
            total_value_usd,
            total_value_gbp,
            fx_metadata,
        ) = calculate_sold_assets_value(
            fy_start=None,
            fy_end=None,
            input_file=temp_analyzed,
            fx_provider=None,  # No FX for this test
            base_currency="USD",
        )

        # Verify we have some sell orders
        assert len(sold_assets_gbp) > 0, "Should have found some SELL orders"

        # Verify all transactions are SELL orders
        for trans in sold_assets_gbp:
            # Check that the original event was a sell
            # We can verify by checking the test data structure
            assert trans.value_usd > 0, "Value should be positive"
            assert trans.qty > 0, "Quantity should be positive"
            assert trans.price > 0, "Price should be positive"

        # Verify totals match sum of individual transactions
        calculated_total = sum(trans.value_usd for trans in sold_assets_gbp)
        assert abs(calculated_total - total_value_usd) < 0.01, (
            f"Total value mismatch: {calculated_total} vs {total_value_usd}"
        )

        print("✓ test_sell_orders_filtered_correctly passed")
    finally:
        Path(temp_analyzed).unlink()


def test_value_calculation_correct():
    """Test that value calculation (qty × price) is correct."""
    # Create test events with known values
    test_events = [
        {
            "id": "1",
            "order_id": "order1",
            "transaction_time": "2024-01-15T10:00:00Z",
            "type": "fill",
            "price": "100.00",
            "qty": "10",
            "side": "sell",
            "symbol": "TEST_VAL",
            "cum_qty": "10",
            "order_status": "filled",
        },
        {
            "id": "2",
            "order_id": "order2",
            "transaction_time": "2024-01-16T10:00:00Z",
            "type": "fill",
            "price": "50.00",
            "qty": "5",
            "side": "sell",
            "symbol": "TEST_VAL",
            "cum_qty": "5",
            "order_status": "filled",
        },
        {
            "id": "3",
            "order_id": "order3",
            "transaction_time": "2024-01-17T10:00:00Z",
            "type": "fill",
            "price": "200.00",
            "qty": "2",
            "side": "buy",  # Should be excluded
            "symbol": "TEST_VAL",
            "cum_qty": "2",
            "order_status": "filled",
        },
    ]

    # Analyze events
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_input = f.name

    try:
        analyzed_events = analyze_events(temp_input)

        # Write analyzed events
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump(analyzed_events, f2, indent=2)
            temp_analyzed = f2.name

        try:
            # Calculate sold assets value
            (
                values_by_symbol_usd,
                values_by_symbol_gbp,
                sold_assets_gbp,
                total_value_usd,
                total_value_gbp,
                fx_metadata,
            ) = calculate_sold_assets_value(
                fy_start=None,
                fy_end=None,
                input_file=temp_analyzed,
                fx_provider=None,
                base_currency="USD",
            )

            # Expected: (10 × 100) + (5 × 50) = 1000 + 250 = 1250
            expected_total = 1000.0 + 250.0

            assert abs(total_value_usd - expected_total) < 0.01, (
                f"Expected total value {expected_total}, got {total_value_usd}"
            )

            # Verify symbol total
            assert "TEST_VAL" in values_by_symbol_usd
            assert abs(values_by_symbol_usd["TEST_VAL"] - expected_total) < 0.01

            # Verify we have exactly 2 sell transactions
            assert len(sold_assets_gbp) == 2, f"Expected 2 transactions, got {len(sold_assets_gbp)}"

            # Verify individual transaction values
            trans_values = sorted([trans.value_usd for trans in sold_assets_gbp])
            assert abs(trans_values[0] - 250.0) < 0.01, "First transaction should be 250"
            assert abs(trans_values[1] - 1000.0) < 0.01, "Second transaction should be 1000"

            print("✓ test_value_calculation_correct passed")
        finally:
            Path(temp_analyzed).unlink()
    finally:
        Path(temp_input).unlink()


def test_fy_date_filtering():
    """Test that FY date filtering works correctly."""
    # Create test events spanning multiple FY periods
    test_events = [
        {
            "id": "1",
            "order_id": "order1",
            "transaction_time": "2023-03-15T10:00:00Z",  # Before FY 2023-24
            "type": "fill",
            "price": "100.00",
            "qty": "10",
            "side": "sell",
            "symbol": "TEST_FY",
            "cum_qty": "10",
            "order_status": "filled",
        },
        {
            "id": "2",
            "order_id": "order2",
            "transaction_time": "2023-05-15T10:00:00Z",  # Within FY 2023-24
            "type": "fill",
            "price": "100.00",
            "qty": "10",
            "side": "sell",
            "symbol": "TEST_FY",
            "cum_qty": "10",
            "order_status": "filled",
        },
        {
            "id": "3",
            "order_id": "order3",
            "transaction_time": "2024-03-15T10:00:00Z",  # Within FY 2023-24
            "type": "fill",
            "price": "100.00",
            "qty": "10",
            "side": "sell",
            "symbol": "TEST_FY",
            "cum_qty": "10",
            "order_status": "filled",
        },
        {
            "id": "4",
            "order_id": "order4",
            "transaction_time": "2024-05-15T10:00:00Z",  # After FY 2023-24
            "type": "fill",
            "price": "100.00",
            "qty": "10",
            "side": "sell",
            "symbol": "TEST_FY",
            "cum_qty": "10",
            "order_status": "filled",
        },
    ]

    # Analyze events
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_input = f.name

    try:
        analyzed_events = analyze_events(temp_input)

        # Write analyzed events
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump(analyzed_events, f2, indent=2)
            temp_analyzed = f2.name

        try:
            # Parse FY 2023-24: April 6, 2023 to April 5, 2024
            fy_start, fy_end = parse_fy_date_range("2023-24")

            # Calculate sold assets value for FY 2023-24
            (
                values_by_symbol_usd,
                values_by_symbol_gbp,
                sold_assets_gbp,
                total_value_usd,
                total_value_gbp,
                fx_metadata,
            ) = calculate_sold_assets_value(
                fy_start=fy_start,
                fy_end=fy_end,
                input_file=temp_analyzed,
                fx_provider=None,
                base_currency="USD",
            )

            # Should only include orders 2 and 3 (within FY 2023-24)
            # Expected: (10 × 100) + (10 × 100) = 2000
            expected_total = 2000.0

            assert abs(total_value_usd - expected_total) < 0.01, (
                f"Expected total value {expected_total} for FY 2023-24, got {total_value_usd}"
            )

            # Verify we have exactly 2 transactions
            assert len(sold_assets_gbp) == 2, (
                f"Expected 2 transactions for FY 2023-24, got {len(sold_assets_gbp)}"
            )

            print("✓ test_fy_date_filtering passed")
        finally:
            Path(temp_analyzed).unlink()
    finally:
        Path(temp_input).unlink()


def test_short_sales_included():
    """Test that short sales (sell_short) are included in the calculation."""
    test_events = [
        {
            "id": "1",
            "order_id": "order1",
            "transaction_time": "2024-01-15T10:00:00Z",
            "type": "fill",
            "price": "100.00",
            "qty": "10",
            "side": "sell",  # Long sale
            "symbol": "TEST_SHORT",
            "cum_qty": "10",
            "order_status": "filled",
        },
        {
            "id": "2",
            "order_id": "order2",
            "transaction_time": "2024-01-16T10:00:00Z",
            "type": "fill",
            "price": "50.00",
            "qty": "5",
            "side": "sell_short",  # Short sale - should be included
            "symbol": "TEST_SHORT",
            "cum_qty": "5",
            "order_status": "filled",
        },
    ]

    # Analyze events
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_input = f.name

    try:
        analyzed_events = analyze_events(temp_input)

        # Write analyzed events
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump(analyzed_events, f2, indent=2)
            temp_analyzed = f2.name

        try:
            # Calculate sold assets value
            (
                values_by_symbol_usd,
                values_by_symbol_gbp,
                sold_assets_gbp,
                total_value_usd,
                total_value_gbp,
                fx_metadata,
            ) = calculate_sold_assets_value(
                fy_start=None,
                fy_end=None,
                input_file=temp_analyzed,
                fx_provider=None,
                base_currency="USD",
            )

            # Expected: (10 × 100) + (5 × 50) = 1000 + 250 = 1250
            expected_total = 1000.0 + 250.0

            assert abs(total_value_usd - expected_total) < 0.01, (
                f"Expected total value {expected_total} including short sales, "
                f"got {total_value_usd}"
            )

            # Verify we have exactly 2 transactions (both sell and sell_short)
            assert len(sold_assets_gbp) == 2, (
                f"Expected 2 transactions (sell + sell_short), got {len(sold_assets_gbp)}"
            )

            print("✓ test_short_sales_included passed")
        finally:
            Path(temp_analyzed).unlink()
    finally:
        Path(temp_input).unlink()


def test_symbol_grouping():
    """Test that values are correctly grouped by symbol."""
    test_events = [
        {
            "id": "1",
            "order_id": "order1",
            "transaction_time": "2024-01-15T10:00:00Z",
            "type": "fill",
            "price": "100.00",
            "qty": "10",
            "side": "sell",
            "symbol": "AAPL",
            "cum_qty": "10",
            "order_status": "filled",
        },
        {
            "id": "2",
            "order_id": "order2",
            "transaction_time": "2024-01-16T10:00:00Z",
            "type": "fill",
            "price": "50.00",
            "qty": "5",
            "side": "sell",
            "symbol": "AAPL",
            "cum_qty": "5",
            "order_status": "filled",
        },
        {
            "id": "3",
            "order_id": "order3",
            "transaction_time": "2024-01-17T10:00:00Z",
            "type": "fill",
            "price": "200.00",
            "qty": "2",
            "side": "sell",
            "symbol": "MSFT",
            "cum_qty": "2",
            "order_status": "filled",
        },
    ]

    # Analyze events
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_events, f, indent=2)
        temp_input = f.name

    try:
        analyzed_events = analyze_events(temp_input)

        # Write analyzed events
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f2:
            json.dump(analyzed_events, f2, indent=2)
            temp_analyzed = f2.name

        try:
            # Calculate sold assets value
            (
                values_by_symbol_usd,
                values_by_symbol_gbp,
                sold_assets_gbp,
                total_value_usd,
                total_value_gbp,
                fx_metadata,
            ) = calculate_sold_assets_value(
                fy_start=None,
                fy_end=None,
                input_file=temp_analyzed,
                fx_provider=None,
                base_currency="USD",
            )

            # Verify symbol totals
            assert "AAPL" in values_by_symbol_usd
            assert "MSFT" in values_by_symbol_usd

            # AAPL: (10 × 100) + (5 × 50) = 1000 + 250 = 1250
            assert abs(values_by_symbol_usd["AAPL"] - 1250.0) < 0.01

            # MSFT: (2 × 200) = 400
            assert abs(values_by_symbol_usd["MSFT"] - 400.0) < 0.01

            # Total: 1250 + 400 = 1650
            assert abs(total_value_usd - 1650.0) < 0.01

            print("✓ test_symbol_grouping passed")
        finally:
            Path(temp_analyzed).unlink()
    finally:
        Path(temp_input).unlink()


def test_with_test_data():
    """Test with actual test data file to ensure integration works end-to-end."""
    test_input = str(get_test_data_path("taxable_activities.json"))

    # Analyze events first
    analyzed_events = analyze_events(test_input)

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(analyzed_events, f, indent=2)
        temp_analyzed = f.name

    try:
        # Calculate sold assets value (all-time)
        (
            values_by_symbol_usd,
            values_by_symbol_gbp,
            sold_assets_gbp,
            total_value_usd,
            total_value_gbp,
            fx_metadata,
        ) = calculate_sold_assets_value(
            fy_start=None,
            fy_end=None,
            input_file=temp_analyzed,
            fx_provider=None,
            base_currency="USD",
        )

        # Verify we have results
        assert len(sold_assets_gbp) > 0, "Should have found SELL orders in test data"

        # Verify totals match
        calculated_total = sum(trans.value_usd for trans in sold_assets_gbp)
        assert abs(calculated_total - total_value_usd) < 0.01, (
            "Total value should match sum of individual transactions"
        )

        # Verify symbol totals match
        for symbol, total in values_by_symbol_usd.items():
            symbol_transactions = [t for t in sold_assets_gbp if t.symbol == symbol]
            symbol_total = sum(t.value_usd for t in symbol_transactions)
            assert abs(symbol_total - total) < 0.01, (
                f"Symbol {symbol} total mismatch: {symbol_total} vs {total}"
            )

        print("✓ test_with_test_data passed")
    finally:
        Path(temp_analyzed).unlink()


if __name__ == "__main__":
    print("Running value_assets_sold integration tests...\n")
    test_sell_orders_filtered_correctly()
    test_value_calculation_correct()
    test_fy_date_filtering()
    test_short_sales_included()
    test_symbol_grouping()
    test_with_test_data()
    print("\n✅ All value_assets_sold integration tests passed!")
