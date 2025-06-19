"""Config flow for Ostrom integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CITY_ID,
    CONF_TARIFF,
    CONF_USAGE,
    CONF_ZIP_CODE,
    DOMAIN,
    OSTROM_API_URL,
    SIMPLY_DYNAMIC,
    SIMPLY_FAIR,
    SIMPLY_FAIR_WITH_PRICE_CAP,
)
from .helper import validate_city_id, validate_zip_code
from .ostrom_rest import OstromClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZIP_CODE): vol.All(
            cv.positive_int,
        ),
        vol.Required(CONF_CITY_ID): vol.All(
            cv.positive_int,
        ),
        vol.Required(CONF_TARIFF): vol.In(
            [SIMPLY_FAIR, SIMPLY_FAIR_WITH_PRICE_CAP, SIMPLY_DYNAMIC]
        ),
        vol.Required(CONF_USAGE): vol.All(
            cv.positive_int, vol.Range(min=600, max=15000)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    if not validate_city_id(data[CONF_CITY_ID]):
        raise InvalidCityId

    if not validate_zip_code(data[CONF_ZIP_CODE]):
        raise InvalidZipCode

    client = OstromClient(OSTROM_API_URL)

    try:
        await client.get_current_price(
            data[CONF_CITY_ID], data[CONF_USAGE], data[CONF_ZIP_CODE]
        )
    except Exception as e:
        raise InvalidAuth from e

    _LOGGER.info("Successfully connected with Ostrom API")

    return {
        "title": "Ostrom Energy " + str(data[CONF_ZIP_CODE]),
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ostrom."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(
                f"ostrom_{user_input[CONF_ZIP_CODE]}_{user_input[CONF_CITY_ID]}"
            )
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidZipCode:
                errors["base"] = "invalid_zip_code"
            except InvalidCityId:
                errors["base"] = "invalid_city_id"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_ZIP_CODE: user_input.get(CONF_ZIP_CODE),
                        CONF_CITY_ID: user_input.get(CONF_CITY_ID),
                        CONF_USAGE: user_input.get(CONF_USAGE),
                        CONF_TARIFF: user_input.get(CONF_TARIFF),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidZipCode(HomeAssistantError):
    """Error to indicate there is an invalid zip code."""


class InvalidCityId(HomeAssistantError):
    """Error to indicate there is an invalid city ID."""
