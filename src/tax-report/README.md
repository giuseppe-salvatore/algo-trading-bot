# Tax Report

Python scripts to process and analyze trading events from Alpaca taxable activities data.

## Overview

This project contains three scripts for processing Alpaca trading activity data:

1. **combine_events.py**: Combines events that share the same `order_id`, intelligently handles partial fills and full fills, removing redundant partial fill events when prices match, and warning about discrepancies.

2. **analyze_events.py**: Analyzes events by grouping them by `order_id`, identifying atomic events, and reconciling events with the same order_id when prices differ. Returns a sorted list of processable events.

3. **balance_tracker.py**: Tracks position balance for a specific symbol, showing buy/sell events, quantities, prices, cost basis, and position status (opened, updated, or closed) in a human-readable format.

## Features

- **Event Combination**: Groups events by `order_id` and combines them intelligently
- **Partial Fill Removal**: Automatically removes partial fill events when prices match, keeping only the final fill event
- **Discrepancy Detection**: Warns when:
  - Events with the same `order_id` have different prices
  - Events with the same `order_id` have different transaction times (at second resolution)
- **JSON Output**: Creates a new combined JSON file in the same format as the input

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

**combine_events:**
```bash
just combine
```

**analyze_events:**
```bash
just analyze
```

**balance_tracker:**
```bash
just balance SYMBOL=AAPL
```

### Output

- **combine_events.py**: Creates `data/taxable_activities_combined.json` with the processed events. The output format matches the input format.

- **analyze_events.py**: Creates `data/taxable_activities_analyzed.json` with a sorted list of processable events (by transaction_time, older first). Events with the same order_id are reconciled into a single event.

- **balance_tracker.py**: Creates `data/{SYMBOL}_balance_report.txt` with a human-readable report showing:
  - Event type (BUY/SELL)
  - Quantity
  - Unit price
  - Cost basis for each transaction
  - Position status with icons (🟢 opened, 🔄 updated, 🔴 closed)
  - Running position balance and average cost

## How It Works

### combine_events.py

1. **Load Events**: Reads all events from `data/taxable_activities.json`
2. **Group by Order ID**: Groups events that share the same `order_id`
3. **Process Groups**:
   - For events with the same `order_id`:
     - If prices are identical: Removes partial fill events, keeps only fill events
     - If prices differ: Keeps all events and prints a warning
     - If transaction times differ (at second resolution): Prints a warning
4. **Generate Output**: Creates a new JSON file with the combined events

**Example:**
- Event 1: `order_id: "abc123"`, `type: "partial_fill"`, `price: "100.00"`
- Event 2: `order_id: "abc123"`, `type: "fill"`, `price: "100.00"`

The output will contain only Event 2 (the fill event), since prices match.

### analyze_events.py

1. **Load Events**: Reads all events from `data/taxable_activities.json`
2. **Group by Order ID**: Groups events that share the same `order_id`
3. **Process Events**:
   - **Atomic Events** (single order_id): Added directly to processable list
   - **Multi-Event Groups** (same order_id):
     - **Same Price**: Discards partial fill events, keeps fill events
     - **Different Prices**: Reconciles events using weighted average price calculation:
       - Weighted average: `(price1 × qty1 + price2 × qty2) / total_qty`
       - Uses final `cum_qty` as total quantity
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
   - Uses average cost basis method for position tracking
   - For **BUY** events:
     - Adds to position
     - Updates average cost basis (weighted average)
     - Marks as 🟢 **opened** if position was 0, or 🔄 **updated** if position existed
   - For **SELL** events:
     - Reduces position proportionally
     - Adjusts cost basis based on sale quantity
     - Marks as 🔄 **updated** if partial sale, or 🔴 **closed** if position goes to 0
4. **Generate Report**: Creates a human-readable text file with transaction details

**Example Output:**
```
Date/Time            Side   Qty          Price        Cost Basis      Status    Position      Avg Cost    
2024-01-15 10:30:00  BUY    10.0000      $150.00      $1,500.00       🟢 opened  10.0000       $150.00
2024-01-20 14:15:00  BUY    5.0000       $155.00      $775.00         🔄 updated 15.0000       $151.67
2024-01-25 11:00:00  SELL   8.0000       $160.00      $1,280.00       🔄 updated 7.0000        $151.67
2024-01-30 09:45:00  SELL   7.0000       $165.00      $1,155.00       🔴 closed  0.0000       -
```

## Notes

- The scripts use only Python standard library modules (`json`, `collections`, `datetime`, `typing`, `pathlib`)
- Transaction time comparison is done at second resolution (microseconds are ignored)
- Warnings are printed to stdout for manual review
- The output file preserves the original JSON structure and formatting
- Scripts automatically resolve paths relative to the project root, so they work regardless of where they're executed from

