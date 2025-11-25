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

# Run balance_tracker script
# Usage: just balance AAPL
balance SYMBOL:
    @echo "Running balance_tracker for symbol {{SYMBOL}}..."
    ./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/balance_tracker.py {{SYMBOL}}

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
    @echo "  just install              - Install all dependencies"
    @echo "  just sync                 - Sync dependencies"
    @echo "  just analyze              - Run analyze_events script"
    @echo "  just balance SYMBOL=X     - Run balance_tracker for symbol X"
    @echo "  just test                 - Run tests"
    @echo "  just lint                 - Lint all Python files"
    @echo "  just format               - Format all Python files"
    @echo "  just info                 - Show workspace information"
