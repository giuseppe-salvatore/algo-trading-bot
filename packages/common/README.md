# Common Package

Shared libraries and utilities for the alpaca-scripts monorepo.

## Purpose

This package contains common code that can be reused across multiple apps in the monorepo. Examples include:

- Shared data processing utilities
- Common configuration helpers
- Shared data models and types
- Reusable business logic

## Usage

To use this package in an app, add it as a dependency in the app's `pyproject.toml`:

```toml
[project]
dependencies = [
    "common @ {path = '../../packages/common', editable = true}"
]
```

Then import from it:

```python
from common import some_utility_function
```

## Development

This package follows the same structure as apps:
- Source code in `src/common/`
- Tests in `tests/`

