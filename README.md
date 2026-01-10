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
just balance SYMBOL=AAPL  # Run balance_tracker for a symbol

# Forex commands
just fetch-rates 15-01-2024 20-01-2024 USD/GBP  # Fetch exchange rates

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
│   └── forex/                # Forex exchange rate tools
│       ├── src/
│       ├── tests/
│       ├── README.md
│       └── pyproject.toml
├── packages/
│   ├── common/               # Shared libraries
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   └── exchange_rate/        # Exchange rate proxy package
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
- `just balance SYMBOL=X` - Track position balance for a symbol

See [apps/tax-report/README.md](apps/tax-report/README.md) for detailed documentation.

### [forex](apps/forex/)

Command-line tools for fetching historical exchange rates from multiple providers. Useful for currency conversion in tax reporting and financial analysis.

**Commands:**
- `just fetch-rates START_DATE END_DATE CURRENCY_PAIR` - Fetch exchange rates for a date range

See [apps/forex/README.md](apps/forex/README.md) for detailed documentation.

## Packages

### [common](packages/common/)

Shared libraries and utilities that can be reused across multiple apps in the monorepo.

See [packages/common/README.md](packages/common/README.md) for more information.

### [exchange_rate](packages/exchange_rate/)

Abstraction layer for fetching historical exchange rates from multiple providers (exchangerate-api.com, openexchangerates.org, APILayer) with intelligent caching and multi-source support. Used by the forex app for currency conversion.

See [packages/exchange_rate/README.md](packages/exchange_rate/README.md) for detailed documentation.

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
