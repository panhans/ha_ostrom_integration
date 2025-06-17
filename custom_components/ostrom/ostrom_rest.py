"""Ostrom REST API client."""

import base64
from datetime import UTC, datetime, timedelta
from typing import TypedDict
from urllib.parse import urlencode, urljoin

import aiohttp
from requests import Response

from homeassistant.exceptions import HomeAssistantError

from .const import (
    OSTROM_API_URL_PROD,
    OSTROM_API_URL_TEST,
    OSTROM_AUTH_URL_PROD,
    OSTROM_AUTH_URL_TEST,
)


class OstromPrice(TypedDict, total=False):
    """Typed ostrom price dict."""

    date: str | None
    netMwhPrice: float | None
    netKwhPrice: float | None
    grossKwhPrice: float | None
    netKwhTaxAndLevies: float | None
    grossKwhTaxAndLevies: float | None
    netMonthlyOstromBaseFee: float | None
    grossMonthlyOstromBaseFee: float | None
    netMonthlyGridFees: float | None
    grossMonthlyGridFees: float | None


class OstromClient:
    """Class to hold client information for the Ostrom API."""

    @property
    def client_id(self) -> str:
        """Returns client id."""
        return self._client_id

    def __init__(self, client_id: str, client_secret: str, sandbox_mode: bool) -> None:
        """Initialize the OstromClientInfo class."""
        self._client_id = client_id
        self._client_secret = client_secret
        self._sandbox_mode = sandbox_mode

        self._access_token: str | None = None
        self._expires_at: datetime = datetime.min

        self._auth_url = (
            OSTROM_AUTH_URL_TEST if self._sandbox_mode else OSTROM_AUTH_URL_PROD
        )
        self._api_url = (
            OSTROM_API_URL_TEST if self._sandbox_mode else OSTROM_API_URL_PROD
        )

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""

        if self._expires_at > datetime.now() and self._access_token:
            return True

        payload = {"grant_type": "client_credentials"}

        auth = f"{self._client_id}:{self._client_secret}"

        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "authorization": "Basic "
            + base64.b64encode(auth.encode("utf-8")).decode("utf-8"),
        }

        url = urljoin(self._auth_url, "oauth2/token")

        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url,
                headers=headers,
                data=payload,
            ) as response,
        ):
            if not response.ok:
                return False
            data = await response.json()
            self._access_token = data["access_token"]
            self._expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
            return True

    async def fetch_ostrom_price_data(
        self,
        zip_code: str,
        start_date: datetime = datetime.min,
        end_date: datetime = datetime.min,
    ) -> list[OstromPrice]:
        """Fetch price data from the Ostrom API."""

        if start_date == end_date == datetime.min:
            start_date = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(hours=12)

        params = {
            "startDate": start_date.isoformat(timespec="milliseconds") + "Z",
            "endDate": end_date.isoformat(timespec="milliseconds") + "Z",
            "resolution": "HOUR",
            "zip": zip_code,
        }

        url = urljoin(self._api_url, "spot-prices")
        url = f"{url}?{urlencode(params)}"

        if await self.authenticate():
            headers = {
                "accept": "application/json",
                "authorization": f"Bearer {self._access_token}",
            }

            async with (
                aiohttp.ClientSession() as session,
                session.get(url, headers=headers) as response,
            ):
                if not response.ok:
                    text = await response.text()
                    raise OstromRestBadRequestException(
                        f"Bad request to Ostrom API: {text}"
                    )
                data = (await response.json())["data"]
                return [OstromPrice(**entry) for entry in data]

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
