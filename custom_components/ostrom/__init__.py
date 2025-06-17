"""The Ostrom integration."""

from __future__ import annotations

import datetime
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ENTITY_ID,
    Platform,
)
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
    CONF_END,
    CONF_SANDBOX,
    CONF_START,
    CONF_ZIP_CODE,
    DOMAIN,
    MANUFACTURER,
    NAME,
    VERSION,
)
from .helper import convert_prices_to_json, get_identifier, get_name
from .ostrom_rest import OstromClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ostrom from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    zip_code = str(entry.data.get(CONF_ZIP_CODE))
    client_id = str(entry.data.get(CONF_CLIENT_ID))
    client_secret = str(entry.data.get(CONF_CLIENT_SECRET))
    is_sandbox_mode = bool(entry.data.get(CONF_SANDBOX))

    client = OstromClient(client_id, client_secret, is_sandbox_mode)
    entry.runtime_data = {"client": client, CONF_ZIP_CODE: zip_code}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Device registration
    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=get_identifier(zip_code, client.client_id),
        manufacturer=MANUFACTURER,
        name=get_name(zip_code),
        model=NAME,
        sw_version=VERSION,
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    # Service registration
    async def get_price_data(call: ServiceCall) -> ServiceResponse:
        """Handle the get_price_data service call."""
        start = call.data.get(CONF_START)
        end = call.data.get(CONF_END)
        if not isinstance(start, datetime.datetime) or not isinstance(
            end, datetime.datetime
        ):
            raise TypeError("start and end must be datetime objects")

        entity_id = call.data.get(CONF_ENTITY_ID)
        if not isinstance(entity_id, str):
            raise TypeError("entity_id must be a string")

        registry = er.async_get(hass)

        reg_entry = registry.async_get(entity_id)
        if reg_entry is None:
            raise ValueError(f"Entity {entity_id} not found in registry")

        entry_id = reg_entry.config_entry_id
        sensor = hass.data[DOMAIN][entry_id]["sensor"]
        zip_code = sensor.zip_code

        result = await client.fetch_ostrom_price_data(zip_code, start, end)

        _LOGGER.info("Ostrom prices: %s", result)

        json_values = convert_prices_to_json(result)

        return {
            "prices": json_values,
        }

    hass.services.async_register(
        domain=DOMAIN,
        service="get_price_data",
        service_func=get_price_data,
        schema=vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID): cv.entity_id,
                vol.Required(CONF_START): cv.datetime,
                vol.Required(CONF_END): cv.datetime,
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
