# Alpaca Scripts - Justfile commands
# Uses PDM for dependency and workspace management
# PDM is installed in the virtual environment

# Default recipe
default:
    @just --list

# Install dependencies for all workspace packages
install:
    @echo "Installing dependencies..."
    ./venv/bin/pdm install

# Sync dependencies (update lock file and install)
sync:
    @echo "Syncing dependencies..."
    ./venv/bin/pdm sync

# Run combine_events script
combine:
    @echo "Running combine_events..."
    ./venv/bin/pdm run -p apps/tax-report python apps/tax-report/src/combine_events.py

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
    @./venv/bin/pdm run pytest apps/*/tests packages/*/tests || echo "No tests found or pytest not installed"

# Show workspace info
info:
    @echo "Workspace information:"
    ./venv/bin/pdm info

# Show help
help:
    @echo "Available commands:"
    @echo "  just install              - Install all dependencies"
    @echo "  just sync                 - Sync dependencies"
    @echo "  just combine              - Run combine_events script"
    @echo "  just analyze              - Run analyze_events script"
    @echo "  just balance SYMBOL=X     - Run balance_tracker for symbol X"
    @echo "  just test                 - Run tests"
    @echo "  just info                 - Show workspace information"
