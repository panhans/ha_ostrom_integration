"""Ostrom Sensor Platform."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_ZIP_CODE, DOMAIN, MANUFACTURER, NAME
from .helper import OstromPrice, get_identifier, get_name
from .ostrom_rest import OstromClient

SCAN_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Ostrom sensor from a config entry."""

    sensor = OstromPriceSensor(
        entry.runtime_data["client"], entry.runtime_data[CONF_ZIP_CODE]
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
        return self._zip_code

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the sensor."""
        return {
            "identifiers": get_identifier(self._zip_code, self._client.client_id),
            "name": get_name(self._zip_code),
            "manufacturer": MANUFACTURER,
            "model": NAME,
        }

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
            "date": self._delegate.get("date") if self._delegate else None,
            "net_mwh_price": self._delegate.get("netMwhPrice")
            if self._delegate
            else None,
            "net_kwh_price": self._delegate.get("netKwhPrice")
            if self._delegate
            else None,
            "gross_kwh_price": self._delegate.get("grossKwhPrice")
            if self._delegate
            else None,
            "net_kwh_tax_and_levies": self._delegate.get("netKwhTaxAndLevies")
            if self._delegate
            else None,
            "gross_kwh_tax_and_levies": self._delegate.get("grossKwhTaxAndLevies")
            if self._delegate
            else None,
            "net_monthly_ostrom_base_fee": self._delegate.get("netMonthlyOstromBaseFee")
            if self._delegate
            else None,
            "gross_monthly_ostrom_base_fee": self._delegate.get(
                "grossMonthlyOstromBaseFee"
            )
            if self._delegate
            else None,
            "net_monthly_grid_fees": self._delegate.get("netMonthlyGridFees")
            if self._delegate
            else None,
            "gross_monthly_grid_fees": self._delegate.get("grossMonthlyGridFees")
            if self._delegate
            else None,
        }

    def __init__(self, client: OstromClient, zip_code: str) -> None:
        """Initialize the sensor."""
        self._client = client
        self._zip_code = zip_code
        self._attr_name = f"Ostrom Energy {zip_code}"
        self._attr_unique_id = f"ostrom_{zip_code}"
        self._attr_native_unit_of_measurement = "ct/kWh"
        self._attr_native_value = None
        self._delegate: OstromPrice | None = None

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""

        key_datetime = datetime.now().replace(minute=0, second=0, microsecond=0)

        response_data = await self._client.fetch_ostrom_price_data(
            self._zip_code, key_datetime, key_datetime + timedelta(hours=1)
        )

        self._delegate = (
            response_data[0] if response_data and len(response_data) > 0 else None
        )
        self._attr_native_value = (
            self._delegate["netKwhPrice"] if self._delegate else None
        )
