#!/usr/bin/env python3
"""
Configuration management for exchange rate providers.

Loads configuration from config file and environment variables.
Environment variables take precedence over config file values.
"""

import json
import os
from pathlib import Path
from typing import Any


def get_project_root() -> Path:
    """Get the project root directory (4 levels up from this file)."""
    # File is at: packages/exchange_rate/src/exchange_rate_config.py
    # Need to go up 4 levels to reach project root
    return Path(__file__).parent.parent.parent.parent


def load_config(config_file: str | Path | None = None) -> dict[str, Any]:
    """
    Load exchange rate configuration from file and environment variables.

    Args:
        config_file: Path to config file. If None, uses default:
            config/exchange_rates.json in project root.

    Returns:
        Dictionary with configuration:
        - providers: Dict of provider configs with api_key
        - cache: Dict with cache directory path
    """
    project_root = get_project_root()

    # Default config file path
    if config_file is None:
        config_file = project_root / "config" / "exchange_rates.json"
    else:
        config_file = Path(config_file)

    # Default configuration
    config: dict[str, Any] = {
        "providers": {
            "exchangerate_api": {"api_key": ""},
            "openexchangerates": {"api_key": ""},
            "apilayer": {"api_key": ""},
        },
        "cache": {"directory": "data/exchange-rates"},
        # Optional: default provider name, used by higher-level tools
        # when no CLI/env override is provided.
        # If not set in file, callers should fall back to a sensible default.
        "default_provider": "exchangerate_api",
    }

    # Load from file if it exists
    if config_file.exists():
        try:
            with open(config_file) as f:
                file_config = json.load(f)
                # Merge providers
                if "providers" in file_config:
                    config["providers"].update(file_config["providers"])
                # Merge cache settings
                if "cache" in file_config:
                    config["cache"].update(file_config["cache"])
                # Allow default provider selection from config
                if "default_provider" in file_config:
                    config["default_provider"] = file_config["default_provider"]
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load config file {config_file}: {e}")

    # Override with environment variables
    # Format: EXCHANGE_RATE_<PROVIDER>_API_KEY
    for provider_name in config["providers"]:
        env_var_name = f"EXCHANGE_RATE_{provider_name.upper()}_API_KEY"
        env_value = os.getenv(env_var_name)
        if env_value:
            config["providers"][provider_name]["api_key"] = env_value

    return config


def get_provider_api_key(provider_name: str, config_file: str | Path | None = None) -> str:
    """
    Get API key for a specific provider.

    Args:
        provider_name: Name of the provider (e.g., "exchangerate_api", "apilayer")
        config_file: Optional path to config file

    Returns:
        API key string (empty string if not set)
    """
    config = load_config(config_file)
    return config["providers"].get(provider_name, {}).get("api_key", "")


def get_cache_directory(config_file: str | Path | None = None) -> Path:
    """
    Get cache directory path.

    Args:
        config_file: Optional path to config file

    Returns:
        Path object for cache directory (relative to project root)
    """
    config = load_config(config_file)
    cache_dir = config["cache"].get("directory", "data/exchange-rates")
    project_root = get_project_root()
    return project_root / cache_dir


def get_default_provider(config_file: str | Path | None = None) -> str:
    """
    Get the default FX provider name.

    This allows higher-level tools (like the tax-report app) to respect a
    default provider defined in config/exchange_rates.json while still
    allowing CLI and environment variable overrides.

    Args:
        config_file: Optional path to config file

    Returns:
        Provider name string. Falls back to "exchangerate_api" if not set.
    """
    config = load_config(config_file)
    provider = config.get("default_provider") or "exchangerate_api"
    return str(provider)
