# Alpaca Scripts - Justfile commands
# Uses PDM for dependency and workspace management
# PDM is installed in the virtual environment

# Default recipe
default:
    @just --list

prepare:
    python3 -m venv venv && ./venv/bin/pip install pdm

# Install dependencies for all workspace packages
install:
    @echo "Installing dependencies..."
    ./venv/bin/pdm install
    ./venv/bin/pip install ruff

# Sync dependencies (update lock file and install)
sync:
    @echo "Syncing dependencies..."
    ./venv/bin/pdm sync

# Run analyze_events script
analyze:
    @echo "Running analyze_events..."
    ./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/analyze_events.py

# Run analyze_events with test data
test-analyze:
    @echo "Running analyze_events on test data..."
    ./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/analyze_events.py \
        --input data/trading/alpaca/test/taxable_activities.json \
        --output data/trading/alpaca/test/taxable_activities_analyzed.json

# Run balance_tracker script
# Usage: just balance AAPL
balance SYMBOL:
    @echo "Running balance_tracker for symbol {{SYMBOL}}..."
    ./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/balance_tracker.py {{SYMBOL}}

# Run balance_tracker with test data
# Usage: just test-balance TEST_POS_OPEN
test-balance SYMBOL:
    @echo "Running balance_tracker for test symbol {{SYMBOL}}..."
    @mkdir -p data/trading/alpaca/test/reports
    @./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/balance_tracker.py {{SYMBOL}} \
        --input data/trading/alpaca/test/taxable_activities_analyzed.json \
        --splits data/trading/alpaca/test/splits.json \
        --output data/trading/alpaca/test/reports/{{SYMBOL}}_balance_report.txt

# Run fiscal_year_report script
# Usage: just fiscal-report 2025-26
fiscal-report FY:
    @echo "Running fiscal_year_report for FY {{FY}}..."
    ./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/fiscal_year_report.py {{FY}}

# Run fiscal_year_report with test data
# Usage: just test-fiscal-report 2025-26
test-fiscal-report FY:
    @echo "Running fiscal_year_report for test FY {{FY}}..."
    ./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/fiscal_year_report.py {{FY}} \
        --input data/trading/alpaca/test/taxable_activities_analyzed.json \
        --splits data/trading/alpaca/test/splits.json \
        --name-changes data/trading/alpaca/test/name_changes.json

# Run fiscal_year_report for all-time analysis (no FY specified)
# Usage: just fiscal-report-all-time
fiscal-report-all-time:
    @echo "Running fiscal_year_report for all-time analysis..."
    ./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/fiscal_year_report.py

# Fetch exchange rates for a date range
# Usage: just fetch-rates 15-01-2024 20-01-2024 USD/GBP
# Optional flags: --provider openexchangerates --output data/rates.csv
# Examples:
#   just fetch-rates 15-01-2024 20-01-2024 USD/GBP
#   just fetch-rates 15-01-2024 20-01-2024 USD/GBP --provider openexchangerates
#   just fetch-rates 01-01-2024 31-01-2024 USD/GBP --provider openexchangerates --output data/rates_jan.csv
fetch-rates START_DATE END_DATE CURRENCY_PAIR *ARGS:
    @echo "Fetching exchange rates from {{START_DATE}} to {{END_DATE}} for {{CURRENCY_PAIR}}..."
    ./venv/bin/pdm run -p apps/forex python apps/forex/src/fetch_rates.py {{START_DATE}} {{END_DATE}} {{CURRENCY_PAIR}} {{ARGS}}

# Run tests for all packages
test:
    @echo "Running tests..."
    @find apps/tax-report/tests -name "test_*.py" -exec sh -c 'echo "=== Running {} ==="; ./venv/bin/python "{}"; echo ""' \;

# Lint all Python files across all sub-projects
lint:
    @echo "Linting Python files..."
    ./venv/bin/ruff check apps/ packages/

# Format all Python files across all sub-projects
format:
    @echo "Formatting Python files..."
    ./venv/bin/ruff format apps/ packages/

# Show workspace info
info:
    @echo "Workspace information:"
    ./venv/bin/pdm info

# Show help
help:
    @echo "Available commands:"
    @echo "Available commands:"
    @echo "  just install              - Install all dependencies"
    @echo "  just sync                 - Sync dependencies"
    @echo "  just analyze              - Run analyze_events script"
    @echo "  just test-analyze         - Run analyze_events on test data"
    @echo "  just balance SYMBOL=X     - Run balance_tracker for symbol X"
    @echo "  just test-balance SYMBOL=X - Run balance_tracker for test symbol X"
    @echo "  just fiscal-report FY=X   - Run fiscal_year_report for FY X (e.g., 2025-26)"
    @echo "  just test-fiscal-report FY=X - Run fiscal_year_report for test FY X"
    @echo "  just fiscal-report-all-time - Run fiscal_year_report for all-time analysis"
    @echo "  just fetch-rates START=X END=Y PAIR=Z [FLAGS] - Fetch exchange rates"
    @echo "    Examples:"
    @echo "      just fetch-rates 15-01-2024 20-01-2024 USD/GBP"
    @echo "      just fetch-rates 15-01-2024 20-01-2024 USD/GBP --provider openexchangerates"
    @echo "      just fetch-rates 01-01-2024 31-01-2024 USD/GBP --provider openexchangerates --output data/rates.csv"
    @echo "  just test                 - Run tests"
    @echo "  just lint                 - Lint all Python files"
    @echo "  just format               - Format all Python files"
    @echo "  just info                 - Show workspace information"
