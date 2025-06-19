"""Ostrom Sensor Platform."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_CITY_ID,
    CONF_TARIFF,
    CONF_USAGE,
    CONF_ZIP_CODE,
    DOMAIN,
    MANUFACTURER,
    NAME,
    SIMPLY_FAIR,
    SIMPLY_FAIR_WITH_PRICE_CAP,
)
from .helper import get_identifier, get_name
from .ostrom_rest import OstromClient, OstromTariff

SCAN_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Ostrom sensor from a config entry."""

    sensor = OstromPriceSensor(
        entry.runtime_data["client"],
        entry.runtime_data[CONF_ZIP_CODE],
        entry.runtime_data[CONF_CITY_ID],
        entry.runtime_data[CONF_USAGE],
        entry.runtime_data[CONF_TARIFF],
    )
    async_add_entities([sensor], update_before_add=True)

    async def update(event_time):
        await sensor.async_update_ha_state(True)

    async_track_time_interval(hass, update, timedelta(minutes=60))

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = {
        "sensor": sensor,
    }


class OstromPriceSensor(SensorEntity):
    """Representation of an Ostrom price sensor."""

    @property
    def zip_code(self) -> str:
        """Returns zip code."""
        return str(self._zip_code)

    @property
    def city_id(self) -> str:
        """Returns zip code."""
        return str(self._city_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the sensor."""
        return {
            "identifiers": get_identifier(str(self._zip_code), str(self._city_id)),
            "name": get_name(str(self._zip_code)),
            "manufacturer": MANUFACTURER,
            "model": NAME,
        }

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID of the sensor."""
        return self._attr_unique_id

    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        value = self._attr_native_value
        match value:
            case None:
                return None
            case float() | int():
                return float(value)
            case str():
                try:
                    return float(value)
                except ValueError:
                    return None
            case Decimal():
                return float(value)
            case date():
                return None
            case _:
                return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {
            "zip_code": self._zip_code,
            "basic_fee": self._delegate.get("basicFee") if self._delegate else None,
            "network_fee": self._delegate.get("networkFee") if self._delegate else None,
            "unit_price_per_kwh": self._delegate.get("unitPricePerkWH")
            if self._delegate
            else None,
            "strom_preis_bremse_unit_price": self._delegate.get(
                "stromPreisBremseUnitPrice"
            )
            if self._delegate
            else None,
        }

    def __init__(
        self, client: OstromClient, zip_code: int, city_id: int, usage: int, tariff: str
    ) -> None:
        """Initialize the sensor."""
        self._client = client
        self._zip_code = zip_code
        self._city_id = city_id
        self._tariff = tariff
        self._usage = usage
        self._attr_name = f"Ostrom Energy {zip_code}"
        self._attr_unique_id = f"ostrom_{zip_code!s}"
        self._attr_native_unit_of_measurement = "ct/kWh"
        self._attr_native_value = None
        self._delegate: OstromTariff | None = None

    async def async_update(self, hass: HomeAssistant) -> None:
        """Fetch new state data for the sensor."""

        tariffs = (
            await self._client.get_current_price(
                self._city_id, self._usage, self._zip_code
            )
            or []
        )

        pattern = "basisProdukt" if SIMPLY_FAIR in self._tariff else "basisDynamic"

        for t in tariffs:
            if t and pattern in str(t.get("productCode")):
                self._delegate = t
                break

        if not self._delegate:
            self._attr_native_value = None
            return

        value = self._delegate.get("unitPricePerkWH")
        price_cap = self._delegate.get("stromPreisBremseUnitPrice")

        if (
            value is not None
            and price_cap is not None
            and float(value) > float(price_cap)
            and self._tariff == SIMPLY_FAIR_WITH_PRICE_CAP
        ):
            value = price_cap

        self._attr_native_value = value
