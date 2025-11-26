#!/usr/bin/env bash
#
# Script to extract all unique symbols from a trading events JSON file
# and generate balance reports for each symbol using balance_tracker.py
#
# Usage: ./generate_all_balance_reports.sh <input_file>
# Example: ./generate_all_balance_reports.sh data/trading/alpaca/live/taxable_activities_analyzed.json

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if input file is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No input file provided${NC}"
    echo "Usage: $0 <input_file>"
    echo "Example: $0 data/trading/alpaca/live/taxable_activities_analyzed.json"
    exit 1
fi

INPUT_FILE="$1"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}Error: Input file not found: $INPUT_FILE${NC}"
    exit 1
fi

# Get the project root (assuming script is in apps/tax-report/scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BALANCE_TRACKER="$PROJECT_ROOT/apps/tax-report/src/balance_tracker.py"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/pdm"

# Check if balance_tracker.py exists
if [ ! -f "$BALANCE_TRACKER" ]; then
    echo -e "${RED}Error: balance_tracker.py not found at: $BALANCE_TRACKER${NC}"
    exit 1
fi

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}Error: Virtual environment not found. Please run 'just install' first.${NC}"
    exit 1
fi

echo -e "${GREEN}Extracting unique symbols from: $INPUT_FILE${NC}"

# Extract unique symbols using Python (more reliable than jq for large files)
# We'll use Python from the venv to ensure compatibility
UNIQUE_SYMBOLS=$(
    "$PROJECT_ROOT/venv/bin/python" -c "
import json
import sys

try:
    with open('$INPUT_FILE', 'r') as f:
        events = json.load(f)
    
    # Extract unique symbols (case-insensitive, but preserve original case)
    symbols = set()
    for event in events:
        symbol = event.get('symbol', '').strip()
        if symbol:
            symbols.add(symbol.upper())
    
    # Sort symbols for consistent output
    for symbol in sorted(symbols):
        print(symbol)
except json.JSONDecodeError as e:
    print(f'Error: Invalid JSON in file: {e}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'Error reading file: {e}', file=sys.stderr)
    sys.exit(1)
"
)

# Check if we got any symbols
if [ -z "$UNIQUE_SYMBOLS" ]; then
    echo -e "${YELLOW}Warning: No symbols found in the input file${NC}"
    exit 0
fi

# Count symbols
SYMBOL_COUNT=$(echo "$UNIQUE_SYMBOLS" | wc -l)
echo -e "${GREEN}Found $SYMBOL_COUNT unique symbol(s)${NC}"
echo ""

# Determine the directory of the input file to find splits and name_changes files
INPUT_DIR="$(cd "$(dirname "$INPUT_FILE")" && pwd)"
SPLITS_FILE="$INPUT_DIR/splits.json"
NAME_CHANGES_FILE="$INPUT_DIR/name_changes.json"

# Build the command prefix
CMD_PREFIX="$VENV_PYTHON run -p apps/tax-report python $BALANCE_TRACKER"

# Track success/failure
SUCCESS_COUNT=0
FAILED_COUNT=0
FAILED_SYMBOLS=()

# Process each symbol
while IFS= read -r symbol; do
    if [ -z "$symbol" ]; then
        continue
    fi
    
    echo -e "${YELLOW}Processing symbol: $symbol${NC}"
    
    # Build command with optional arguments
    CMD="$CMD_PREFIX $symbol --input $INPUT_FILE"
    
    # Add splits file if it exists
    if [ -f "$SPLITS_FILE" ]; then
        CMD="$CMD --splits $SPLITS_FILE"
    fi
    
    # Add name_changes file if it exists
    if [ -f "$NAME_CHANGES_FILE" ]; then
        CMD="$CMD --name-changes $NAME_CHANGES_FILE"
    fi
    
    # Run the command
    if eval "$CMD"; then
        echo -e "${GREEN}✓ Successfully processed $symbol${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}✗ Failed to process $symbol${NC}"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_SYMBOLS+=("$symbol")
    fi
    echo ""
    
done <<< "$UNIQUE_SYMBOLS"

# Print summary
echo "=========================================="
echo -e "${GREEN}Summary:${NC}"
echo "  Total symbols: $SYMBOL_COUNT"
echo -e "  ${GREEN}Successful: $SUCCESS_COUNT${NC}"
if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "  ${RED}Failed: $FAILED_COUNT${NC}"
    echo ""
    echo -e "${RED}Failed symbols:${NC}"
    for sym in "${FAILED_SYMBOLS[@]}"; do
        echo "    - $sym"
    done
else
    echo -e "  ${GREEN}Failed: 0${NC}"
fi
echo "=========================================="

# Exit with error if any failed
if [ $FAILED_COUNT -gt 0 ]; then
    exit 1
fi

exit 0

