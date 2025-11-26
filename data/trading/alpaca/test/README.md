# Test Data Documentation

This directory contains test data files for the tax-report application. These files are used for automated testing and development purposes.

## Files

- **`taxable_activities.json`**: Test trading events covering various scenarios
- **`splits.json`**: Test stock split events for forward and backward split scenarios
- **`taxable_activities_analyzed.json`**: Generated file containing analyzed/reconciled events (created after running `analyze_events`)

## Test Stock Symbols and Scenarios

The test data includes the following test stocks, each designed to exercise a specific scenario or edge case:

### TEST_POS_OPEN
**Scenario**: Position remains open at the end of all events

**Events**:
- Buy 10 shares at $100
- Buy 5 more shares at $110
- Sell 7 shares at $120

**Expected Result**: Position open with 8 shares remaining (10 + 5 - 7)

**Purpose**: Tests that the system correctly tracks positions that remain open after all trading activity.

---

### TEST_FW_SPLIT
**Scenario**: Forward stock split (3:1) with position closure

**Events**:
- Buy 10 shares at $100
- Forward split occurs (3:1) - 10 shares become 30 shares
- Sell all 30 shares at $35

**Expected Result**: Position closed after split (all shares sold)

**Purpose**: Tests forward split handling where shares are multiplied and the position is eventually closed.

**Note**: Requires `splits.json` for the split event.

---

### TEST_BW_SPLIT
**Scenario**: Backward stock split (1:3) with position closure

**Events**:
- Buy 30 shares at $100
- Backward split occurs (1:3) - 30 shares become 10 shares
- Sell all 10 shares at $300

**Expected Result**: Position closed after split (all shares sold)

**Purpose**: Tests backward/reverse split handling where shares are reduced and the position is eventually closed.

**Note**: Requires `splits.json` for the split event.

---

### TEST_SHORT
**Scenario**: Short-only positions with covering

**Events**:
- Short sell 10 shares at $100
- Short sell 5 more shares at $110
- Cover 15 shares at $90 (covering all shorts)

**Expected Result**: Position closed (all shorts covered)

**Purpose**: Tests short position tracking and covering scenarios.

---

### TEST_PARTIAL_FILL
**Scenario**: Order with multiple partial fills at different prices

**Events**:
- Partial fill: Buy 5 shares at $50
- Partial fill: Buy 5 shares at $51
- Fill: Buy 10 shares at $52 (total order: 20 shares)
- Sell 20 shares at $60

**Expected Result**: Events properly reconciled using weighted average price and cum_qty; position closed

**Purpose**: Tests partial fill reconciliation and weighted average price calculation when prices differ across partial fills.

---

### TEST_REVERSE_LONG
**Scenario**: Long position reversed to short (selling more than owned)

**Events**:
- Buy 5 shares at $100 (open long position)
- Sell 10 shares at $110 (selling more than owned)

**Expected Result**: Long position closed, short position opened with 5 shares

**Purpose**: Tests the edge case where selling more shares than owned converts a long position to a short position.

---

### TEST_REVERSE_SHORT
**Scenario**: Short position reversed to long (buying more than shorted)

**Events**:
- Short sell 5 shares at $100 (open short position)
- Buy 10 shares at $90 (buying more than shorted)

**Expected Result**: Short position closed, long position opened with 5 shares

**Purpose**: Tests the edge case where buying more shares than shorted converts a short position to a long position.

---

## File Structure

### taxable_activities.json

Each event in this file follows the Alpaca taxable activities format:

```json
{
    "id": "unique-event-id",
    "activity_type": "FILL",
    "transaction_time": "2024-01-01T10:00:00Z",
    "type": "fill",
    "price": "100.00",
    "qty": "10",
    "side": "buy",
    "symbol": "TEST_POS_OPEN",
    "leaves_qty": "0",
    "order_id": "order-id",
    "cum_qty": "10",
    "order_status": "filled"
}
```

Key fields:
- `symbol`: Test stock symbol (all prefixed with `TEST_`)
- `side`: `"buy"` or `"sell"`
- `qty`: Quantity of shares (string representation of number)
- `price`: Price per share (string representation of number)
- `type`: `"fill"` or `"partial_fill"`
- `cum_qty`: Cumulative quantity filled for the order
- `order_id`: Unique order identifier (events with same `order_id` will be reconciled)

### splits.json

Split events follow this format with REMOVE and ADD pairs:

```json
{
    "id": "split-id",
    "activity_type": "SPLIT",
    "date": "2024-02-01",
    "created_at": "2024-02-01T12:00:00Z",
    "net_amount": "0",
    "description": "REMOVE, From QTY:10, To QTY:30, Position Value:1000.00",
    "symbol": "TEST_FW_SPLIT",
    "qty": "-10",
    "price": "100.00",
    "status": "executed"
}
```

## Usage

### Running Tests

The test data is used by the integration tests. Run all tests:

```bash
just test
```

Run integration scenario tests specifically:

```bash
./venv/bin/python apps/tax-report/tests/test_integration_scenarios.py
```

### Using Test Data for Development

To analyze test data:

```bash
just test-analyze
```

This creates `taxable_activities_analyzed.json` from the test events.

To generate a balance report for a test symbol:

```bash
just test-balance TEST_POS_OPEN
```

This will:
1. Use the analyzed test events
2. Use the test splits file
3. Generate a balance report in the test directory

### Manual Script Usage

You can also use the scripts directly with test data:

```bash
# Analyze test events
./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/analyze_events.py \
    --input data/trading/alpaca/test/taxable_activities.json \
    --output data/trading/alpaca/test/taxable_activities_analyzed.json

# Generate balance report
./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/balance_tracker.py TEST_POS_OPEN \
    --input data/trading/alpaca/test/taxable_activities_analyzed.json \
    --splits data/trading/alpaca/test/splits.json \
    --output data/trading/alpaca/test/TEST_POS_OPEN_balance_report.txt
```

## Notes

- All test data uses the `TEST_` prefix to clearly indicate these are test symbols
- Prices and quantities are realistic but arbitrary
- Test data is version-controlled (unlike live data which is git-ignored)
- When adding new test scenarios, update this README to document them

