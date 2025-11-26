# Tests for Tax Report

This directory contains tests to ensure the tax-report processing pipeline works correctly.

## Running Tests

Run all tests:
```bash
python3 apps/tax-report/tests/test_analyze_events.py
python3 apps/tax-report/tests/test_balance_tracker.py
python3 apps/tax-report/tests/test_integration.py
```

Or run them all at once:
```bash
for test in apps/tax-report/tests/test_*.py; do python3 "$test"; done
```

## Test Coverage

### test_analyze_events.py
- Tests event reconciliation when prices are the same
- Tests event reconciliation when prices differ (weighted average)
- Tests that `cum_qty` is correctly used instead of individual `qty` values
- **Critical bug fix**: Ensures partial fills are correctly reconciled to use `cum_qty` from fill events

### test_balance_tracker.py
- Tests LONG->SHORT position conversion (splits into close/open events)
- Tests SHORT->LONG position conversion (splits into close/open events)
- Tests quantity verification across events
- Tests that `cum_qty` values are correctly handled
- Tests symbol name change handling (consolidates events from old and new symbol names)

### test_integration.py
- Tests the full pipeline from raw events -> analyzed -> balance tracking
- Tests quantity consistency across the entire pipeline
- Verifies that the bug fix works end-to-end

## Known Issues Fixed

### Bug: Missing Shares in Partial Fills
**Issue**: When multiple partial fills with the same `order_id` and price were reconciled, the code was using the `qty` from the fill event (e.g., 9) instead of the `cum_qty` (e.g., 20), resulting in missing shares.

**Example**:
- 4 events: 8 + 1 + 2 + 9 shares (partial fills + fill)
- Fill event has `qty: 9` but `cum_qty: 20`
- Old code: Used `qty: 9` ❌
- New code: Uses `cum_qty: 20` ✅

**Fix**: Updated `reconcile_events()` in `analyze_events.py` to use `cum_qty` from fill events when all prices are the same.

## Adding New Tests

When adding new functionality or fixing bugs:

1. Add a test case that reproduces the issue
2. Verify the test fails before the fix
3. Implement the fix
4. Verify the test passes
5. Add edge cases if applicable

