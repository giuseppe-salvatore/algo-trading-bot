#!/usr/bin/env python3
"""
Configuration management for Alpaca API client.

Loads configuration from config file and environment variables.
Environment variables take precedence over config file values.
"""

import json
import os
from pathlib import Path
from typing import Any


def get_project_root() -> Path:
    """Get the project root directory (4 levels up from this file)."""
    # File is at: packages/alpaca-api/src/alpaca_api/alpaca_config.py
    # Need to go up 4 levels to reach project root
    return Path(__file__).parent.parent.parent.parent


def load_config(config_file: str | Path | None = None) -> dict[str, Any]:
    """
    Load Alpaca API configuration from file and environment variables.

    Args:
        config_file: Path to config file. If None, uses default:
            config/alpaca-api.json in project root.

    Returns:
        Dictionary with configuration:
        - api_key: Alpaca API key
        - api_secret: Alpaca API secret
        - base_url: Base URL for API (defaults to live)
        - environment: "live" or "paper" (defaults to "live")
    """
    project_root = get_project_root()

    # Default config file path
    if config_file is None:
        config_file = project_root / "config" / "alpaca-api.json"
    else:
        config_file = Path(config_file)

    # Default configuration
    config: dict[str, Any] = {
        "api_key": "",
        "api_secret": "",
        "base_url": "https://api.alpaca.markets",
        "environment": "live",
    }

    # Load from file if it exists
    if config_file.exists():
        try:
            with open(config_file) as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load config file {config_file}: {e}")

    # Override with environment variables
    env_api_key = os.getenv("ALPACA_API_KEY")
    if env_api_key:
        config["api_key"] = env_api_key

    env_api_secret = os.getenv("ALPACA_API_SECRET")
    if env_api_secret:
        config["api_secret"] = env_api_secret

    env_base_url = os.getenv("ALPACA_BASE_URL")
    if env_base_url:
        config["base_url"] = env_base_url
    elif os.getenv("ALPACA_ENVIRONMENT") == "paper":
        # If environment is paper and base_url not set, use paper URL
        config["base_url"] = "https://paper-api.alpaca.markets"
        config["environment"] = "paper"

    env_environment = os.getenv("ALPACA_ENVIRONMENT")
    if env_environment:
        config["environment"] = env_environment
        # Auto-set base_url if not explicitly set
        if not env_base_url:
            if env_environment == "paper":
                config["base_url"] = "https://paper-api.alpaca.markets"
            else:
                config["base_url"] = "https://api.alpaca.markets"

    return config


def get_api_key(config_file: str | Path | None = None) -> str:
    """
    Get Alpaca API key.

    Args:
        config_file: Optional path to config file

    Returns:
        API key string (empty string if not set)
    """
    config = load_config(config_file)
    return config.get("api_key", "")


def get_api_secret(config_file: str | Path | None = None) -> str:
    """
    Get Alpaca API secret.

    Args:
        config_file: Optional path to config file

    Returns:
        API secret string (empty string if not set)
    """
    config = load_config(config_file)
    return config.get("api_secret", "")


def get_base_url(config_file: str | Path | None = None) -> str:
    """
    Get Alpaca API base URL.

    Args:
        config_file: Optional path to config file

    Returns:
        Base URL string (defaults to live API URL)
    """
    config = load_config(config_file)
    return config.get("base_url", "https://api.alpaca.markets")
