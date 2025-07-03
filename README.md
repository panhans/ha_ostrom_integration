# ⚡️ Ostrom integration for Home Assistant

This integration provides a sensor and a service for querying electricity prices from Ostrom. The sensor is updated hourly and displays the current electricity price.
With the service, you can query the daily prices. Based on this, you can create automations to start devices, for example, to run household appliances like washing machines when electricity prices are low.

<p align=center>[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=panhans&repository=ha_ostrom_integration&category=Integration)
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Q5Q3QEH52)</p>


## 🧭 Sensor

| Name                          | Datatpye  | Type     | Descripton                 |
|-------------------------------|---------- |----------|----------------------------|
| State                         | float     | state    | current price              |
| zip_code                      | int       | attribut | postal code                |
| basic_fee                     | float     | attribut | Basic fee                  |
| network_fee                   | float     | attribut | Netwrok fee / Netzentgelte |
| unit_price_per_kwh            | float     | attribut | current price / state      |
| strom_preis_bremse_unit_price | float     | attribut | price cap                  |
| unit_of_measurement           | str       | attribut | unit (cent/kWh)            |
| friendly_name                 | str       | attribut | sensor name                |

## 💿 Service

| Parameter | Descripton |
| --------- | ---------- |
| Entity ID | Entity ID of your Ostrom Price Sensor |
| Resolution | - Hourly for the prices of the current day </br> - Monthly for the average price of a month |

#### ⏱️ Result hourly

```yaml
prices:
  - date: "2025-06-19T00:00:00.000Z"
    dateUTC: "2025-06-18T22:00:00.000Z"
    price: 11.22
    grossKwhPrice: 13.36
    mWhPriceInEuros: 112.2
    hour: "00"
    taxesAndLevies: 15
    priceWithTaxesAndLevies: 26.22
  - date: "2025-06-19T01:00:00.000Z"
    dateUTC: "2025-06-18T23:00:00.000Z"
    price: 10.64
    grossKwhPrice: 12.67
    mWhPriceInEuros: 106.4
    hour: "01"
    taxesAndLevies: 14.89
    priceWithTaxesAndLevies: 25.53
```

#### 📅 Result monthly

```yaml
prices:
  - price: 6.87
    month: 2025-05
    taxesAndLevies: 14.17
    priceWithTaxesAndLevies: 21.04
  - price: 7.79
    month: 2025-04
    taxesAndLevies: 14.35
    priceWithTaxesAndLevies: 22.14
```
