"""The Ostrom integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)

from .const import (
    CONF_CITY_ID,
    CONF_HOURLY,
    CONF_MONTHLY,
    CONF_RESOLUTION,
    CONF_TARIFF,
    CONF_USAGE,
    CONF_ZIP_CODE,
    DOMAIN,
    MANUFACTURER,
    NAME,
    OSTROM_API_URL,
    VERSION,
)
from .helper import convert_prices_to_json, get_identifier, get_name
from .ostrom_rest import OstromClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ostrom from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    zip_code = int(entry.data.get(CONF_ZIP_CODE) or -1)
    city_id = int(entry.data.get(CONF_CITY_ID) or -1)
    tariff = str(entry.data.get(CONF_TARIFF))
    usage = int(entry.data.get(CONF_USAGE) or -1)

    client = OstromClient(OSTROM_API_URL)
    entry.runtime_data = {
        "client": client,
        CONF_ZIP_CODE: zip_code,
        CONF_TARIFF: tariff,
        CONF_CITY_ID: city_id,
        CONF_USAGE: usage,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Device registration
    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=get_identifier(str(zip_code), str(city_id)),
        manufacturer=MANUFACTURER,
        name=get_name(str(zip_code)),
        model=NAME,
        sw_version=VERSION,
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    async def spot_prices(call: ServiceCall) -> ServiceResponse:
        """Handle the spot_prices service call."""

        entity_id = call.data.get(CONF_ENTITY_ID)
        resolution = call.data.get(CONF_RESOLUTION)

        if not isinstance(entity_id, str):
            raise TypeError("entity_id must be a string")

        registry = er.async_get(hass)

        reg_entry = registry.async_get(entity_id)
        if reg_entry is None:
            raise ValueError(f"Entity {entity_id} not found in registry")

        entry_id = reg_entry.config_entry_id
        sensor = hass.data[DOMAIN][entry_id]["sensor"]
        zip_code = sensor.zip_code
        city_id = sensor.city_id

        result: Any = []
        if resolution == CONF_HOURLY:
            result = await client.spot_prices_hourly(city_id, zip_code)
        elif resolution == CONF_MONTHLY:
            result = await client.spot_prices_monthly(city_id, zip_code)

        json_values = convert_prices_to_json(result)
        return {
            "prices": json_values,
        }

    hass.services.async_register(
        domain=DOMAIN,
        service="spot_prices",
        service_func=spot_prices,
        schema=vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID): cv.entity_id,
                vol.Required(CONF_RESOLUTION): vol.In([CONF_HOURLY, CONF_MONTHLY]),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
