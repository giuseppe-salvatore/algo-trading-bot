# Alpaca Scripts

A monorepo containing Python scripts and tools for processing and analyzing Alpaca trading data.

## Overview

This repository uses a monorepo structure with [PDM](https://pdm.fming.dev/) (Python Dependency Manager) for workspace management and [just](https://github.com/casey/just) for convenient command execution. The project is organized into apps (applications/scripts) and packages (shared libraries) within the workspace.

## Requirements

- Python 3.12 or higher
- [PDM](https://pdm.fming.dev/) - Python Dependency Manager
- [just](https://github.com/casey/just) command runner (optional, but recommended)

## Installation

### Prerequisites

1. **Install just** (optional but recommended):
   ```bash
   # On macOS
   brew install just
   
   # On Linux (using cargo)
   # First, install rustup if you don't have it (required for newer Rust versions):
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source ~/.cargo/env
   
   # Then install just
   cargo install just
   
   # Or download from https://github.com/casey/just/releases
   ```
   
   **Note on Ubuntu 24.04**: The Rust version from `apt` may be too old. Use `rustup` (as shown above) to get a compatible Rust version.

2. **Prepare the project environment** (creates virtual environment and installs PDM):
   ```bash
   just prepare
   ```
   
   This command will:
   - Create a Python virtual environment at `./venv`
   - Install PDM in the virtual environment
   
   **Note**: PDM is installed in the project's virtual environment. The `justfile` automatically uses `./venv/bin/pdm`, so you don't need PDM in your global PATH.

3. **Install dependencies**:
   ```bash
   just install
   ```
   
   Or manually:
   ```bash
   ./venv/bin/pdm install
   ```

## Quick Start

### Running Commands

The easiest way to run scripts is using the provided `justfile`:

```bash
# Tax reporting commands
just analyze              # Run analyze_events script
just balance AAPL         # Run balance_tracker for a symbol
# Generate balance reports for all symbols:
# apps/tax-report/scripts/generate_all_balance_reports.sh data/trading/alpaca/live/taxable_activities_analyzed.json

# Forex commands
just fetch-rates 15-01-2024 20-01-2024 USD/GBP  # Fetch exchange rates

# Alpaca data fetching commands
pdm run -p apps/fetch-trades python apps/fetch-trades/src/fetch_trades.py --after 2020-07-07 --until 2025-11-24
pdm run -p apps/fetch-dividends python apps/fetch-dividends/src/fetch_dividends.py --after 2020-07-07 --until 2025-11-24

# Development commands
just install    # Install all dependencies
just sync       # Sync dependencies
just test       # Run tests
just info       # Show workspace information
```

### Running with PDM Directly

You can also run scripts directly with PDM:

```bash
# Run tax-report scripts
pdm run analyze-events
pdm run balance-tracker AAPL
```

## Project Structure

```
alpaca-scripts/
├── apps/
│   ├── tax-report/           # Tax reporting application
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   ├── forex/                # Forex exchange rate tools
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   ├── fetch-trades/         # Fetch trading activities from Alpaca
│   │   ├── src/
│   │   ├── README.md
│   │   └── pyproject.toml
│   └── fetch-dividends/      # Fetch dividend activities from Alpaca
│       ├── src/
│       ├── README.md
│       └── pyproject.toml
├── packages/
│   ├── common/               # Shared libraries
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   ├── exchange_rate/        # Exchange rate proxy package
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   └── alpaca-api/           # Alpaca API client package
│       ├── src/
│       ├── tests/
│       ├── README.md
│       └── pyproject.toml
├── config/                   # Configuration files
├── data/                     # Shared data files
├── pyproject.toml            # Root workspace configuration
├── justfile                  # Command runner configuration
└── README.md                 # This file
```

## Apps

### [tax-report](apps/tax-report/)

Scripts for processing and analyzing trading events from Alpaca taxable activities data. Includes tools for combining events, analyzing order patterns, and tracking position balances.

**Commands:**
- `just analyze` - Analyze and reconcile events
- `just balance AAPL` - Track position balance for a symbol (replace AAPL with your symbol)
- `apps/tax-report/scripts/generate_all_balance_reports.sh <input_file>` - Generate balance reports for all symbols

See [apps/tax-report/README.md](apps/tax-report/README.md) for detailed documentation.

### [forex](apps/forex/)

Command-line tools for fetching historical exchange rates from multiple providers. Useful for currency conversion in tax reporting and financial analysis.

**Commands:**
- `just fetch-rates START_DATE END_DATE CURRENCY_PAIR` - Fetch exchange rates for a date range

See [apps/forex/README.md](apps/forex/README.md) for detailed documentation.

### [fetch-trades](apps/fetch-trades/)

Command-line tool for fetching trading activities (FILL, NC, SPLIT) from Alpaca API. Saves data to timestamped daily folders to avoid overriding existing data.

**Commands:**
- `pdm run -p apps/fetch-trades python apps/fetch-trades/src/fetch_trades.py [--after DATE] [--until DATE]` - Fetch trading activities

See [apps/fetch-trades/README.md](apps/fetch-trades/README.md) for detailed documentation.

### [fetch-dividends](apps/fetch-dividends/)

Command-line tool for fetching dividend activities (DIV) from Alpaca API. Saves data to timestamped daily folders to avoid overriding existing data.

**Commands:**
- `pdm run -p apps/fetch-dividends python apps/fetch-dividends/src/fetch_dividends.py [--after DATE] [--until DATE]` - Fetch dividend activities

See [apps/fetch-dividends/README.md](apps/fetch-dividends/README.md) for detailed documentation.

## Packages

### [common](packages/common/)

Shared libraries and utilities that can be reused across multiple apps in the monorepo.

See [packages/common/README.md](packages/common/README.md) for more information.

### [exchange_rate](packages/exchange_rate/)

Abstraction layer for fetching historical exchange rates from multiple providers (exchangerate-api.com, openexchangerates.org, APILayer) with intelligent caching and multi-source support. Used by the forex app for currency conversion.

See [packages/exchange_rate/README.md](packages/exchange_rate/README.md) for detailed documentation.

### [alpaca-api](packages/alpaca-api/)

Alpaca API client package providing a clean interface for fetching account activities (trade events, dividends, name changes, splits, etc.) from the Alpaca REST API. Used by the fetch-trades and fetch-dividends apps.

See [packages/alpaca-api/README.md](packages/alpaca-api/README.md) for detailed documentation.

## Workspace Management

This monorepo uses PDM workspaces to manage multiple packages and apps. Key features:

- **Workspace support**: All apps and packages are managed in a single workspace
- **Shared dependencies**: Common dependencies can be defined at the root level
- **Local packages**: Apps can reference shared packages using editable installs
- **Script entry points**: Each app defines its scripts in its `pyproject.toml`

### Adding a New App

1. Create a new directory under `apps/`:
   ```bash
   mkdir -p apps/my-app/src apps/my-app/tests
   ```

2. Create `apps/my-app/pyproject.toml`:
   ```toml
   [project]
   name = "my-app"
   version = "0.1.0"
   requires-python = ">=3.12"
   dependencies = []

   [project.scripts]
   my-script = "my_script:main"

   [tool.pdm]
   package-dir = "src"
   ```

3. Add your source code to `apps/my-app/src/`

4. Run `pdm install` to sync the workspace

### Adding a New Package

1. Create a new directory under `packages/`:
   ```bash
   mkdir -p packages/my-package/src/my_package packages/my-package/tests
   ```

2. Create `packages/my-package/pyproject.toml`:
   ```toml
   [project]
   name = "my-package"
   version = "0.1.0"
   requires-python = ">=3.12"
   dependencies = []

   [tool.pdm]
   package-dir = "src"
   ```

3. Add your source code to `packages/my-package/src/my_package/`

4. To use it in an app, add to the app's `pyproject.toml`:
   ```toml
   [project]
   dependencies = [
       "my-package @ {path = '../../packages/my-package', editable = true}"
   ]
   ```

5. Run `pdm install` to sync the workspace

## License

This project is for personal use.
