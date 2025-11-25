# Alpaca Scripts

A monorepo containing Python scripts and tools for processing and analyzing Alpaca trading data.

## Overview

This repository uses a monorepo structure with [Pants](https://www.pantsbuild.org/) for build management and [just](https://github.com/casey/just) for convenient command execution. The project is organized into subprojects within the `src/` directory, each focused on specific functionality.

## Requirements

- Python 3.10 or higher
- [Pants](https://www.pantsbuild.org/) build system
- [just](https://github.com/casey/just) command runner (optional, but recommended)

## Installation

### Prerequisites

1. **Install Pants**: Follow the [Pants installation guide](https://www.pantsbuild.org/docs/installation). The project includes a `pants` binary wrapper that will bootstrap Pants automatically.

2. **Install just** (optional but recommended):
   ```bash
   # On macOS
   brew install just
   
   # On Linux (using cargo)
   cargo install just
   
   # Or download from https://github.com/casey/just/releases
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
just lint        # Lint code
just format      # Format code
just typecheck   # Type check code
just test        # Run tests
just clean       # Clean Pants cache
```

### Running with Pants Directly

You can also run scripts directly with Pants:

```bash
# Run tax-report scripts
./pants run src/tax-report:combine_events
./pants run src/tax-report:analyze_events
./pants run src/tax-report:balance_tracker -- AAPL
```

## Projects

### [tax-report](src/tax-report/)

Scripts for processing and analyzing trading events from Alpaca taxable activities data. Includes tools for combining events, analyzing order patterns, and tracking position balances.

**Commands:**
- `just combine` - Combine events with the same order_id
- `just analyze` - Analyze and reconcile events
- `just balance SYMBOL=X` - Track position balance for a symbol

See [src/tax-report/README.md](src/tax-report/README.md) for detailed documentation.

## Project Structure

```
alpaca-scripts/
├── src/
│   └── tax-report/              # Tax reporting subproject
│       ├── combine_events.py
│       ├── analyze_events.py
│       ├── balance_tracker.py
│       ├── BUILD
│       └── README.md
├── data/                        # Data files (gitignored)
├── pants.toml                   # Pants configuration
├── justfile                     # Command runner configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

The project is organized as a monorepo to support future shared libraries and multiple subprojects.

## License

This project is for personal use.
