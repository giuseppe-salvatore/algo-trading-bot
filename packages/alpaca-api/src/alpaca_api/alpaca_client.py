#!/usr/bin/env python3
"""
Alpaca API client for fetching account activities.

Provides a clean interface for fetching trade events, dividends, and other
account activities from the Alpaca REST API.
"""

import logging
from typing import Any

import requests

from alpaca_api.activity_types import DIV, FILL, NC, SPLIT
from alpaca_api.models import ActivityData

# Set up logging
logger = logging.getLogger(__name__)


class AlpacaClient:
    """
    Client for interacting with Alpaca REST API.

    Handles authentication, pagination, and provides convenience methods
    for fetching different types of account activities.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.alpaca.markets",
    ):
        """
        Initialize Alpaca client.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: Base URL for API (defaults to live API)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.activities_base_url = f"{self.base_url}/v2/account/activities"

        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required")

    def _get_headers(self) -> dict[str, str]:
        """Get authentication headers for API requests."""
        return {
            "accept": "application/json",
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

    def get_activities(
        self,
        activity_type: str,
        after: str | None = None,
        until: str | None = None,
        page_size: int = 100,
        page_token: str | None = None,
        fetch_all_pages: bool = True,
    ) -> list[ActivityData]:
        """
        Fetch account activities of a specific type.

        Args:
            activity_type: Type of activity (e.g., "DIV", "FILL", "NC", "SPLIT")
            after: Fetch activities after this date (YYYY-MM-DD format)
            until: Fetch activities until this date (YYYY-MM-DD format)
            page_size: Number of results per page (default: 100, max: 100)
            page_token: Token for pagination (for fetching specific page)
            fetch_all_pages: If True, automatically fetch all pages.
                           If False, return only the first page.

        Returns:
            List of activity dictionaries

        Raises:
            requests.RequestException: If API request fails
            ValueError: If invalid parameters provided
        """
        if page_size > 100:
            raise ValueError("page_size cannot exceed 100")

        # Build URL
        url = f"{self.activities_base_url}/{activity_type}"
        params: dict[str, Any] = {
            "direction": "desc",
            "page_size": min(page_size, 100),
        }

        if after:
            params["after"] = after
        if until:
            params["until"] = until
        if page_token:
            params["page_token"] = page_token

        all_activities: list[ActivityData] = []

        try:
            while True:
                response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if not isinstance(data, list):
                    logger.warning(f"Unexpected response format: {type(data)}")
                    break

                all_activities.extend(data)

                # Check if we should fetch more pages
                if not fetch_all_pages:
                    break

                # If we got fewer results than page_size, we're done
                if len(data) < page_size:
                    break

                # Get page_token from last item for next page
                if len(data) > 0 and "id" in data[-1]:
                    params["page_token"] = data[-1]["id"]
                else:
                    break

                logger.debug(f"Fetched {len(data)} activities, total: {len(all_activities)}")

        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                if e.response.status_code == 401:
                    raise ValueError("Authentication failed. Check your API key and secret.") from e
                elif e.response.status_code == 403:
                    raise ValueError("Access forbidden. Check your API permissions.") from e
                elif e.response.status_code == 429:
                    raise ValueError("Rate limit exceeded. Please try again later.") from e
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch activities: {e}")
            raise

        logger.info(f"Fetched {len(all_activities)} {activity_type} activities")
        return all_activities

    def get_dividends(
        self, after: str | None = None, until: str | None = None
    ) -> list[ActivityData]:
        """
        Fetch dividend activities.

        Args:
            after: Fetch dividends after this date (YYYY-MM-DD format)
            until: Fetch dividends until this date (YYYY-MM-DD format)

        Returns:
            List of dividend activity dictionaries
        """
        return self.get_activities(DIV, after=after, until=until)

    def get_trade_fills(
        self, after: str | None = None, until: str | None = None
    ) -> list[ActivityData]:
        """
        Fetch trade fill activities (order executions).

        Args:
            after: Fetch fills after this date (YYYY-MM-DD format)
            until: Fetch fills until this date (YYYY-MM-DD format)

        Returns:
            List of trade fill activity dictionaries
        """
        return self.get_activities(FILL, after=after, until=until)

    def get_name_changes(
        self, after: str | None = None, until: str | None = None
    ) -> list[ActivityData]:
        """
        Fetch name change activities.

        Args:
            after: Fetch name changes after this date (YYYY-MM-DD format)
            until: Fetch name changes until this date (YYYY-MM-DD format)

        Returns:
            List of name change activity dictionaries
        """
        return self.get_activities(NC, after=after, until=until)

    def get_splits(self, after: str | None = None, until: str | None = None) -> list[ActivityData]:
        """
        Fetch stock split activities.

        Args:
            after: Fetch splits after this date (YYYY-MM-DD format)
            until: Fetch splits until this date (YYYY-MM-DD format)

        Returns:
            List of split activity dictionaries
        """
        return self.get_activities(SPLIT, after=after, until=until)
