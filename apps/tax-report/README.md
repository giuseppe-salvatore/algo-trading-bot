# Tax Report

Python scripts to process and analyze trading events from Alpaca taxable activities data.

## Overview

This project contains two scripts for processing Alpaca trading activity data:

1. **analyze_events.py**: Analyzes events by grouping them by `order_id`, identifying atomic events, and reconciling events with the same order_id. Correctly uses `cum_qty` for total quantities. This is the script used by `balance_tracker.py`.

2. **balance_tracker.py**: Tracks position balance for a specific symbol, showing buy/sell events, quantities, prices, cost basis, and position status (opened, updated, or closed) in a human-readable format. Calculates profit/loss on every sale using the Average Cost Basis method.

## Features

- **Event Reconciliation**: Groups events by `order_id` and reconciles them intelligently
- **Partial Fill Handling**: Correctly uses `cum_qty` to determine total quantities from partial fills
- **Weighted Average Pricing**: When prices differ for the same order, calculates weighted average
- **Position Tracking**: Maintains running position balance with average cost basis
- **Profit/Loss Calculation**: Calculates profit/loss on every sale (partial or full) using Average Cost Basis method
- **Discrepancy Detection**: Warns when events with the same `order_id` have different prices or transaction times

## Usage

### Input File

Place your `taxable_activities.json` file in the `data/` directory (at the project root). The file should contain an array of trading event objects with the following structure:

```json
{
    "id": "20251031111548138::799d324d-28c5-4c84-869c-130de20f9e16",
    "activity_type": "FILL",
    "transaction_time": "2025-10-31T15:15:48.138503Z",
    "type": "fill",
    "price": "657.82",
    "qty": "0.5",
    "side": "buy",
    "symbol": "META",
    "leaves_qty": "0",
    "order_id": "b2f0d9e4-bd5b-4968-953c-1b78d58bc44e",
    "cum_qty": "0.5",
    "order_status": "filled"
}
```

### Running the Scripts

**analyze_events:**
```bash
just analyze
```

**balance_tracker:**
```bash
just balance SYMBOL=AAPL
```

### Output

- **analyze_events.py**: Creates `data/taxable_activities_analyzed.json` with a sorted list of processable events (by transaction_time, older first). Events with the same order_id are reconciled into a single event with correct total quantities using `cum_qty`.

- **balance_tracker.py**: Creates `data/{SYMBOL}_balance_report.txt` with a human-readable report showing:
  - Event type (BUY/SELL)
  - Quantity
  - Unit price
  - Cost basis for each transaction
  - Position status with icons (🟢 opened, 🔄 updated, 🔴 closed)
  - Running position balance and average cost
  - Profit/loss for each sale
  - Accumulated gains

## How It Works

### analyze_events.py

1. **Load Events**: Reads all events from `data/taxable_activities.json`
2. **Group by Order ID**: Groups events that share the same `order_id`
3. **Process Events**:
   - **Atomic Events** (single order_id): Added directly to processable list
   - **Multi-Event Groups** (same order_id):
     - **Same Price**: Discards partial fill events, keeps fill events with highest `cum_qty`
     - **Different Prices**: Reconciles events using weighted average price calculation:
       - Weighted average: `(price1 × qty1 + price2 × qty2) / total_qty`
       - Uses final `cum_qty` as total quantity (from the event with latest timestamp)
       - Uses earliest `transaction_time` from the group
4. **Sort and Output**: Sorts all processable events by `transaction_time` (older first) and creates a new JSON file

**Example with different prices:**
- Event 1: `order_id: "abc123"`, `type: "partial_fill"`, `price: "100.00"`, `qty: "10"`, `cum_qty: "10"`
- Event 2: `order_id: "abc123"`, `type: "fill"`, `price: "100.50"`, `qty: "5"`, `cum_qty: "15"`

The output will contain a single reconciled event with:
- Weighted average price: `(100.00 × 10 + 100.50 × 5) / 15 = 100.167`
- Total quantity: `15` (from final cum_qty)
- Transaction time: earliest from the group

### balance_tracker.py

1. **Load Analyzed Events**: Reads events from `data/taxable_activities_analyzed.json`
2. **Filter by Symbol**: Filters events for the specified symbol
3. **Track Position Balance**:
   - Maintains running position quantity and cost basis
   - Uses **Average Cost Basis** method for position tracking and profit calculation
   - For **BUY** events:
     - Adds to position
     - Updates average cost basis (weighted average)
     - Marks as 🟢 **opened** if position was 0, or 🔄 **updated** if position existed
   - For **SELL** events:
     - Calculates profit/loss: `Sale Proceeds - (Quantity Sold × Average Cost)`
     - Reduces position proportionally
     - Adjusts cost basis based on sale quantity
     - Marks as 🔄 **updated** if partial sale, or 🔴 **closed** if position goes to 0
     - Updates accumulated gains
4. **Generate Report**: Creates a human-readable text file with transaction details

**Example Output:**
```
Date/Time            Side   Qty          Price        Cost Basis      Status    Position      Avg Cost    Profit        Accumulated Gains
2024-01-15 10:30:00  BUY    10.0000      $150.00      $1,500.00       🟢 opened  10.0000       $150.00     -              -
2024-01-20 14:15:00  BUY    5.0000       $155.00      $775.00         🔄 updated 15.0000       $151.67     -              -
2024-01-25 11:00:00  SELL   8.0000       $160.00      $1,280.00       🔄 updated 7.0000        $151.67     $66.64         $66.64
2024-01-30 09:45:00  SELL   7.0000       $165.00      $1,155.00       🔴 closed  0.0000       -            $93.33         $159.97
```

## Tax Accounting

This system uses the **Average Cost Basis** method for calculating profit/loss. See [TAX_ACCOUNTING.md](TAX_ACCOUNTING.md) for detailed information about:
- How profit/loss is calculated
- Tax compliance notes
- Comparison with other methods (FIFO, Specific Identification)

## Notes

- The scripts use only Python standard library modules (`json`, `collections`, `datetime`, `typing`, `pathlib`)
- Transaction time comparison uses proper datetime parsing for accurate sorting
- Warnings are printed to stdout for manual review
- The output file preserves the original JSON structure and formatting
- Scripts automatically resolve paths relative to the project root, so they work regardless of where they're executed from
- Profit/loss is calculated on every sale (partial or full), which is correct for tax reporting
