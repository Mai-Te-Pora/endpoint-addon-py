# Python Endpoint Addon

## Summary
The Python programs in this repository are used to enable additional REST API endpoints. Using Docker and Docker Compose, these can be run directly on any Tradehub Sentry Node or on an extra server.

## Endpoints
### Richlist
Richlist Endpoint allows querying the richest wallets for any known coin.

### Trading
The Trading API Endpoint allows querying the trading volume per wallet. A distinction is made between Maker and Taker volume. The trading fees already paid or earned can also be queried.

### Price
A small API endpoint that should be helpful to quickly get the current exchange rates for the well-known Tradehub Coins. Furthermore, the retrieval of historical exchange rates with multiple formatting is possible.  