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

1. **Set up Python virtual environment** (if not already done):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/macOS
   ```

2. **Install PDM in the virtual environment**:
   ```bash
   pip install pdm
   ```
   Or follow the [PDM installation guide](https://pdm.fming.dev/latest/#installation).
   
   **Note**: PDM is installed in the project's virtual environment. The `justfile` automatically uses `./venv/bin/pdm`, so you don't need PDM in your global PATH.

3. **Install just** (optional but recommended):
   ```bash
   # On macOS
   brew install just
   
   # On Linux (using cargo)
   cargo install just
   
   # Or download from https://github.com/casey/just/releases
   ```

4. **Install dependencies**:
   ```bash
   just install
   # or
   ./venv/bin/pdm install
   ```

## Quick Start

### Running Commands

The easiest way to run scripts is using the provided `justfile`:

```bash
# Tax reporting commands
just combine              # Run combine_events script
just analyze              # Run analyze_events script
just balance SYMBOL=AAPL  # Run balance_tracker for a symbol

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
pdm run combine-events
pdm run analyze-events
pdm run balance-tracker AAPL
```

## Project Structure

```
alpaca-scripts/
├── apps/
│   └── tax-report/          # Tax reporting application
│       ├── src/
│       │   ├── combine_events.py
│       │   ├── analyze_events.py
│       │   └── balance_tracker.py
│       ├── tests/            # Test files
│       ├── README.md         # App-specific documentation
│       └── pyproject.toml     # App configuration
├── packages/
│   └── common/               # Shared libraries
│       ├── src/
│       │   └── common/
│       ├── tests/
│       ├── README.md
│       └── pyproject.toml
├── data/                     # Shared data files
├── pyproject.toml            # Root workspace configuration
├── justfile                  # Command runner configuration
└── README.md                 # This file
```

## Apps

### [tax-report](apps/tax-report/)

Scripts for processing and analyzing trading events from Alpaca taxable activities data. Includes tools for combining events, analyzing order patterns, and tracking position balances.

**Commands:**
- `just combine` - Combine events with the same order_id
- `just analyze` - Analyze and reconcile events
- `just balance SYMBOL=X` - Track position balance for a symbol

See [apps/tax-report/README.md](apps/tax-report/README.md) for detailed documentation.

## Packages

### [common](packages/common/)

Shared libraries and utilities that can be reused across multiple apps in the monorepo.

See [packages/common/README.md](packages/common/README.md) for more information.

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
