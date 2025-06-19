"""Helper functions for Ostrom integration in Home Assistant."""

import datetime

import voluptuous as vol

from homeassistant.util.json import JsonValueType

from .const import DOMAIN, NAME


def validate_zip_code(v: int) -> bool:
    """Validate that the zip code is a valid Ostrom zip code."""
    return len(str(v)) == 5


def validate_city_id(v: int) -> bool:
    """Validate that the city ID is a valid Ostrom city ID."""
    return len(str(v)) == 4


def validate_iso_datetime(value):
    """Validate that the input is a valid ISO 8601 datetime string."""
    try:
        return datetime.fromisoformat(value)
    except ValueError as e:
        raise vol.Invalid(
            "Invalid date. Expecting ISO 8601 format (e.g. 2025-06-13T10:00:00)"
        ) from e


def get_identifier(zip_code: str, city_id: str) -> set[tuple[str, str]]:
    """Generate a unique identifier for the Ostrom integration based on the config entry."""
    identifier = f"{zip_code}_{city_id}"
    return {(DOMAIN, identifier)}


def get_name(zip_code: str) -> str:
    """Generate a name for the Ostrom integration based on the config entry."""
    return f"{NAME} {zip_code}"


def _to_json_value(val: object) -> JsonValueType:
    if isinstance(val, (str, int, float, dict, list)) or val is None:
        return val
    return str(val)


def convert_prices_to_json(prices) -> list[JsonValueType]:
    """Convert a list of OstromPrice dictionaries to a list of JSON-compatible dictionaries."""
    return [{k: _to_json_value(v) for k, v in price.items()} for price in prices]
