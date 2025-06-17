"""Config flow for Ostrom integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import CONF_SANDBOX, CONF_ZIP_CODE, DOMAIN, OSTROM_DEV_PORTAL_URL
from .helper import is_valid_plz
from .ostrom_rest import OstromClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): cv.string,
        vol.Required(CONF_CLIENT_SECRET): cv.string,
        vol.Required(CONF_ZIP_CODE): cv.string,
        vol.Required(CONF_SANDBOX): cv.boolean,
    }
)

# a809a30c86d76f9d2a03c473b8c0e25
# e32a80ac2b47cf8120c70eba5792fc54e4a55bd6f38cf4e77cb94e3317a6cd7


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    if not is_valid_plz(data[CONF_ZIP_CODE]):
        raise InvalidZipCode

    client = OstromClient(
        data[CONF_CLIENT_ID] or "",
        data[CONF_CLIENT_SECRET] or "",
        bool(data[CONF_SANDBOX]),
    )

    auth = await client.authenticate()

    if not auth:
        raise InvalidAuth

    _LOGGER.info("Successfully authenticated with Ostrom API")

    return {
        "title": "Ostrom Energy " + data[CONF_ZIP_CODE],
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
            await self.async_set_unique_id(user_input[CONF_ZIP_CODE])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidZipCode:
                errors["base"] = "invalid_zip_code"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_CLIENT_ID: user_input[CONF_CLIENT_ID],
                        CONF_CLIENT_SECRET: user_input[CONF_CLIENT_SECRET],
                        CONF_SANDBOX: user_input[CONF_SANDBOX],
                        CONF_ZIP_CODE: user_input[CONF_ZIP_CODE],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            description_placeholders={
                "link": OSTROM_DEV_PORTAL_URL,
            },
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidZipCode(HomeAssistantError):
    """Error to indicate there is an invalid zip code."""
