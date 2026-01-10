# Tax Report

Python scripts to process and analyze trading events from Alpaca taxable activities data.

## Overview

This project contains three scripts for processing Alpaca trading activity data:

1. **analyze_events.py**: Analyzes events by grouping them by `order_id`, identifying atomic events, and reconciling events with the same order_id. Correctly uses `cum_qty` for total quantities. This is the script used by `balance_tracker.py` and `fiscal_year_report.py`.

2. **balance_tracker.py**: Tracks position balance for a specific symbol, showing buy/sell events, quantities, prices, cost basis, and position status (opened, updated, or closed) in a human-readable format. Calculates profit/loss on every sale using the Average Cost Basis method.

3. **fiscal_year_report.py**: Generates comprehensive UK Financial Year or all-time capital gains reports across all symbols. Processes all events from day 0 to maintain accurate cost basis, but only counts profits from events within the specified FY period (or all events for all-time analysis). Generates reports in text, JSON, and CSV formats.

## Features

- **Event Reconciliation**: Groups events by `order_id` and reconciles them intelligently
- **Partial Fill Handling**: Correctly uses `cum_qty` to determine total quantities from partial fills
- **Weighted Average Pricing**: When prices differ for the same order, calculates weighted average
- **Position Tracking**: Maintains running position balance with average cost basis
- **Profit/Loss Calculation**: Calculates profit/loss on every sale (partial or full) using Average Cost Basis method
- **Discrepancy Detection**: Warns when events with the same `order_id` have different prices or transaction times
- **Stock Splits**: Automatically applies stock splits based on splits.json file
- **Symbol Name Changes**: Automatically consolidates events from symbols that have changed names (e.g., MF → MFLTF → MFLTY)
- **UK Financial Year Reporting**: Generates tax reports for specific UK FY periods (April 6 to April 5)
- **All-Time Analysis**: Option to generate comprehensive profit/loss reports across entire trading history
- **Multi-Format Reports**: Generates reports in text, JSON, and CSV formats

## Usage

### Input File

Place your `taxable_activities.json` file in the `data/trading/alpaca/live/` directory (at the project root). The file should contain an array of trading event objects with the following structure:

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

Or with custom input/output files:
```bash
./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/analyze_events.py \
    --input path/to/input.json \
    --output path/to/output.json
```

**balance_tracker:**
```bash
just balance AAPL
```

Or with custom input/splits/name-changes/output files:
```bash
./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/balance_tracker.py AAPL \
    --input path/to/analyzed.json \
    --splits path/to/splits.json \
    --name-changes path/to/name_changes.json \
    --output path/to/report.txt
```

**generate_all_balance_reports (generate reports for all symbols):**
```bash
# First, make the script executable (if not already)
chmod +x apps/tax-report/scripts/generate_all_balance_reports.sh

# Run with default analyzed events file
apps/tax-report/scripts/generate_all_balance_reports.sh data/trading/alpaca/live/taxable_activities_analyzed.json

# Or with a custom input file
apps/tax-report/scripts/generate_all_balance_reports.sh path/to/analyzed.json
```

This script extracts all unique symbols from the analyzed events file and generates a balance report for each one. It automatically uses the `splits.json` and `name_changes.json` files from the same directory as the input file. Reports are saved to the `reports/` subdirectory (same location as individual balance reports).

**fiscal_year_report:**
```bash
# For a specific UK Financial Year (e.g., 2025-26 = April 6, 2025 to April 5, 2026)
just fiscal-report 2025-26

# For all-time analysis (all events from day 0)
just fiscal-report-all-time
```

Or with custom input/splits/name-changes/output files:
```bash
./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/fiscal_year_report.py 2025-26 \
    --input path/to/analyzed.json \
    --splits path/to/splits.json \
    --name-changes path/to/name_changes.json \
    --output-dir path/to/output/
```

### Command-Line Options

**analyze_events.py:**
- `--input` / `-i`: Override input file path (default: `data/trading/alpaca/live/taxable_activities.json`)
- `--output` / `-o`: Override output file path (default: `data/trading/alpaca/live/taxable_activities_analyzed.json`)

**balance_tracker.py:**
- `SYMBOL` (required): Stock symbol to track (can be old or new name if symbol has changed)
- `--input` / `-i`: Override input analyzed events file (default: `data/trading/alpaca/live/taxable_activities_analyzed.json`)
- `--splits` / `-s`: Override splits file path (default: `data/trading/alpaca/live/splits.json`)
- `--name-changes` / `-n`: Override name_changes.json file path (default: `data/trading/alpaca/live/name_changes.json`)
- `--output` / `-o`: Override output report file (default: `data/trading/alpaca/live/reports/{LATEST_SYMBOL}_balance_report.txt`)

**generate_all_balance_reports.sh:**
- `INPUT_FILE` (required): Path to the analyzed events JSON file (e.g., `taxable_activities_analyzed.json`)
- The script automatically uses `splits.json` and `name_changes.json` from the same directory as the input file
- Reports are generated in the `reports/` subdirectory of the input file's directory
- Provides a summary with success/failure counts for all symbols processed

**fiscal_year_report.py:**
- `FY` (optional): UK Financial Year in format "YYYY-YY" (e.g., "2025-26"). If omitted, performs all-time analysis.
- `--input` / `-i`: Override input analyzed events file (default: `data/trading/alpaca/live/taxable_activities_analyzed.json`)
- `--splits` / `-s`: Override splits file path (default: `data/trading/alpaca/live/splits.json`)
- `--name-changes` / `-n`: Override name_changes.json file path (default: `data/trading/alpaca/live/name_changes.json`)
- `--output-dir` / `-o`: Override output directory (default: `data/tax-return/reports/`)

### Output

- **analyze_events.py**: Creates `data/trading/alpaca/live/taxable_activities_analyzed.json` (by default) with a sorted list of processable events (by transaction_time, older first). Events with the same order_id are reconciled into a single event with correct total quantities using `cum_qty`.

- **balance_tracker.py**: Creates `data/trading/alpaca/live/reports/{SYMBOL}_balance_report.txt` (by default) with a human-readable report showing:
  - Event type (BUY/SELL)
  - Quantity
  - Unit price
  - Cost basis for each transaction
  - Position status with icons (🟢 opened, 🔄 updated, 🔴 closed)
  - Running position balance and average cost
  - Profit/loss for each sale
  - Accumulated gains

- **generate_all_balance_reports.sh**: Generates balance reports for all unique symbols found in the analyzed events file. Each report is saved as `{SYMBOL}_balance_report.txt` in the `reports/` subdirectory. The script provides a summary showing:
  - Total number of symbols found
  - Number of successfully processed symbols
  - Number of failed symbols (if any)
  - List of failed symbols (if any)

- **fiscal_year_report.py**: Creates three report files in `data/tax-return/reports/`:
  - **Text report** (`FY_YYYY-YY_capital_gains_report.txt` or `all_time_capital_gains_report.txt`):
    - Summary with total profit/loss
    - Gains by symbol, sorted by profit (highest first)
    - Separate sections for gains and losses
  - **JSON report** (`.json`): Structured data with FY period, totals, and per-symbol breakdown
  - **CSV report** (`.csv`): Simple format with symbol and profit/loss columns

## How It Works

### analyze_events.py

1. **Load Events**: Reads all events from `data/trading/alpaca/live/taxable_activities.json` (default)
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

1. **Load Analyzed Events**: Reads events from `data/trading/alpaca/live/taxable_activities_analyzed.json` (default)
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

### fiscal_year_report.py

1. **Load and Analyze Events**: Reads all events from `data/trading/alpaca/live/taxable_activities_analyzed.json` (default) and processes them using `analyze_events()` function
2. **Process ALL Events Chronologically**: 
   - Processes ALL events from day 0 (not filtered by date) to maintain accurate position state and cost basis
   - This is critical: positions opened before the FY period need full history to calculate correct profit when selling during the FY
3. **Normalize Symbols**: Resolves all symbols to their latest names using name changes mapping
4. **Track Positions Per Symbol**: For each symbol:
   - Maintains position state (quantity, cost basis, average cost) across all events
   - Applies stock splits chronologically as they occur
   - Processes all buy/sell events to maintain accurate cost basis
5. **Filter Taxable Events**: Only counts profits from taxable events:
   - **Long positions**: SELL transactions (partial or full)
   - **Short positions**: BUY transactions when covering shorts (partial or full)
   - Events must occur within the specified FY period (or all events for all-time analysis)
6. **Generate Reports**: Creates text, JSON, and CSV reports with:
   - Total profit/loss for the period
   - Breakdown by symbol, sorted by profit (highest first)
   - Separate sections for gains and losses

**Example Output (Text Report):**
```
================================================================================
UK Financial Year Capital Gains Report
Financial Year: 2025-26 (April 06, 2025 to April 05, 2026)
================================================================================

Summary:
--------------------------------------------------------------------------------
Total Profit/Loss: $3,665.08
Number of Symbols with Gains: 14
Number of Symbols with Losses: 2

Gains by Symbol (sorted by profit, highest first):
--------------------------------------------------------------------------------
Symbol                   Profit/Loss
--------------------------------------------------------------------------------
INTC                       $1,537.44
TSLA                         $562.72
AMD                          $527.39
...
```

**Key Points:**
- Processes ALL events from day 0 to maintain accurate cost basis calculations
- Only counts profits for events within the specified FY period (when FY is provided)
- For all-time analysis, counts all taxable profits across entire trading history
- Uses the same Average Cost Basis method as `balance_tracker.py` for consistency
- Handles stock splits, symbol name changes, and complex position transitions

## Test Data

The project includes comprehensive test data covering various edge cases and scenarios. See [data/trading/alpaca/test/README.md](../../data/trading/alpaca/test/README.md) for:
- Available test scenarios and what they target
- How to use test data for development and testing
- Examples of running scripts with test data

Test data files are located in `data/trading/alpaca/test/` and are version-controlled (unlike live data which is git-ignored).

## Tax Accounting

This system uses the **Average Cost Basis** method for calculating profit/loss. See [TAX_ACCOUNTING.md](TAX_ACCOUNTING.md) for detailed information about:
- How profit/loss is calculated
- Tax compliance notes
- Comparison with other methods (FIFO, Specific Identification)

## Data Organization

- **Live Data**: Confidential trading data is stored in `data/trading/alpaca/live/` and is git-ignored
- **Test Data**: Test data for development and testing is stored in `data/trading/alpaca/test/` and is version-controlled
- **Tax Reports**: Financial year and all-time capital gains reports are stored in `data/tax-return/reports/` and are git-ignored
- Scripts default to using live data locations but can be overridden with command-line arguments

## Notes

- The scripts use only Python standard library modules (`json`, `collections`, `datetime`, `typing`, `pathlib`, `argparse`)
- Transaction time comparison uses proper datetime parsing for accurate sorting
- Warnings are printed to stdout for manual review
- The output file preserves the original JSON structure and formatting
- Scripts automatically resolve paths relative to the project root, so they work regardless of where they're executed from
- Profit/loss is calculated on every sale (partial or full), which is correct for tax reporting
- Stock splits are automatically applied based on splits.json file (defaults to same directory as input file)
- **Symbol name changes**: When a symbol changes names (e.g., MF → MFLTF → MFLTY), the script automatically:
  - Accepts either the old or new symbol name as input
  - Consolidates events from all related symbol names
  - Generates the report using the latest symbol name
  - Creates a symlink from the old symbol name to the latest report (if input was old name)
  - Displays name change history in the report header
