"""Ostrom REST API client."""

from typing import TypedDict
from urllib.parse import urlencode, urljoin

import aiohttp
from requests import Response

from homeassistant.exceptions import HomeAssistantError


class OstromTariff(TypedDict, total=False):
    """Typed ostrom tariff dict."""

    productCode: str | None
    tariff: float | None
    savings: float | None
    basicFee: float | None
    networkFee: float | None
    unitPricePerkWH: float | None
    tariffWithStormPreisBremse: float | None
    stromPreisBremseUnitPrice: float | None
    accumulatedUnitPriceWithStromPreisBremse: float | None
    unitPrice: float | None
    energyConsumption: float | None
    basePriceBrutto: float | None
    workingPriceBrutto: float | None
    workingPriceNetto: float | None
    meterChargeBrutto: float | None
    workingPricePowerTax: float | None


class OstromSpotPriceHourly(TypedDict, total=False):
    """Typed ostrom spot price dict."""

    date: str | None
    dateUTC: str | None
    price: float | None
    grossKwhPrice: float | None
    mWhPriceInEuros: float | None
    hour: int | None
    taxesAndLevies: float | None
    priceWithTaxesAndLevies: float | None


class OstromSpotPriceMonthly(TypedDict, total=False):
    """Typed ostrom spot price dict."""

    price: float | None
    month: str | None
    taxesAndLevies: float | None
    priceWithTaxesAndLevies: float | None


class OstromClient:
    """Class to hold client information for the Ostrom API."""

    def __init__(self, api_url: str) -> None:
        """Initialize the OstromClientInfo class."""

        self._api_url = api_url

    async def spot_prices_hourly(
        self, city_id: int, zip_code: int
    ) -> list[OstromSpotPriceHourly]:
        """Fetch the current price from the Ostrom API."""

        params = {
            "cityId": city_id,
            "postalCode": zip_code,
        }

        url = urljoin(self._api_url, "v1/spot-prices/ostrom-product-tariff")
        url = f"{url}?{urlencode(params)}"

        async with (
            aiohttp.ClientSession() as session,
            session.get(url) as response,
        ):
            if not response.ok:
                text = await response.text()
                raise OstromRestBadRequestException(
                    f"Bad request to Ostrom API: {text}"
                )
            data = (await response.json())["day"]["prices"]
            return [OstromSpotPriceHourly(**entry) for entry in data]

        return []

    async def spot_prices_monthly(
        self, city_id: int, zip_code: int
    ) -> list[OstromSpotPriceMonthly]:
        """Fetch the current price from the Ostrom API."""

        params = {
            "cityId": city_id,
            "postalCode": zip_code,
        }

        url = urljoin(self._api_url, "v1/spot-prices/ostrom-product-tariff")
        url = f"{url}?{urlencode(params)}"

        async with (
            aiohttp.ClientSession() as session,
            session.get(url) as response,
        ):
            if not response.ok:
                text = await response.text()
                raise OstromRestBadRequestException(
                    f"Bad request to Ostrom API: {text}"
                )
            data = (await response.json())["year"]["prices"]
            return [OstromSpotPriceMonthly(**entry) for entry in data]

        return []

    async def get_current_price(
        self, city_id: int, usage: int, zip_code: int
    ) -> list[OstromTariff] | None:
        """Fetch the current price from the Ostrom API."""

        params = {
            "cityId": city_id,
            "usage": usage,
            "postalCode": zip_code,
        }

        url = urljoin(self._api_url, "v1/tariffs/city-id")
        url = f"{url}?{urlencode(params)}"

        async with (
            aiohttp.ClientSession() as session,
            session.get(url) as response,
        ):
            if not response.ok:
                text = await response.text()
                raise OstromRestBadRequestException(
                    f"Bad request to Ostrom API: {text}"
                )
            data = (await response.json())["ostrom"]
            return [OstromTariff(**entry) for entry in data]

        return []


def raise_ostrom_bad_request_exception(
    response: Response, message: str = "Bad request to Ostrom API"
) -> None:
    """Raise a bad request exception with the response text."""
    raise OstromRestBadRequestException(f"{message}: {response.text}")


def raise_ostrom_unknown_exception(message: str = "Unknown error with Ostrom API"):
    """Raise an unknown exception with a message."""
    raise OstromRestUnknownException(message)


class OstromRestUnknownException(HomeAssistantError):
    """Error to indicate an unknown error occurred with the Ostrom REST API."""


class OstromRestBadRequestException(HomeAssistantError):
    """Error to indicate a bad request was made to the Ostrom REST API."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(message)
        self.message = message
