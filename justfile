# Alpaca Scripts - Justfile commands
# Uses Pants for build and execution

# Default recipe
default:
    @just --list

# Run combine_events script
combine:
    @echo "Running combine_events..."
    ./pants run src/tax-report:combine_events

# Run analyze_events script
analyze:
    @echo "Running analyze_events..."
    ./pants run src/tax-report:analyze_events

# Run balance_tracker script
# Usage: just balance SYMBOL=AAPL
balance SYMBOL:
    @echo "Running balance_tracker for symbol {{SYMBOL}}..."
    ./pants run src/tax-report:balance_tracker -- {{SYMBOL}}

# Lint code
lint:
    @echo "Linting code..."
    ./pants lint ::

# Format code
format:
    @echo "Formatting code..."
    ./pants fmt ::

# Type check code
typecheck:
    @echo "Type checking code..."
    ./pants typecheck ::

# Run tests (if any)
test:
    @echo "Running tests..."
    ./pants test ::

# Clean Pants cache
clean:
    @echo "Cleaning Pants cache..."
    ./pants clean-all

# Show help
help:
    @echo "Available commands:"
    @echo "  just combine              - Run combine_events script"
    @echo "  just analyze              - Run analyze_events script"
    @echo "  just balance SYMBOL=X     - Run balance_tracker for symbol X"
    @echo "  just lint                 - Lint code"
    @echo "  just format               - Format code"
    @echo "  just typecheck            - Type check code"
    @echo "  just test                 - Run tests"
    @echo "  just clean                - Clean Pants cache"

