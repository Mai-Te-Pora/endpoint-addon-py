# Python Endpoint Addon

## Summary
The Python programs in this repository are used to enable additional REST API endpoints. Using Docker and Docker Compose, these can be run directly on any Tradehub Sentry Node or on an extra server.

## Requirements
[Docker](https://docs.docker.com/engine/install/ubuntu/) and [Docker Compose](https://docs.docker.com/compose/install/) is currently the easiest and most convenient option, as all necessary dependencies are installed.


## Setup
### Docker

Clone the repository in a directory.

`git clone https://github.com/Mai-Te-Pora/endpoint-addon-py.git`

Go into the cloned repository.

`cd endpoint-addon-py`

Create the docker images. All required dependencies will be installed into the image.

`docker-compose build`

Start all services as background daemon task.

`docker-compose up -d --force-recreate` 

All services can be stopped with:

`docker-compose stop`

Docker provides the possibility to attach to the terminal logs.

`docker logs -f endpoint-addon-py_richlist_1`

## Endpoints
### Richlist
Richlist Endpoint allows querying the richest wallets for any known coin.

`/richlist/get_denoms`

This endpoint will provide a list with all tracked denoms. To all of these returned denoms there is a rich list.

`/{denom}/top`

By providing a denom the endpoint returns the first 10 entries of the rich list. Supported query parameters are `limit` and `offset` to implement pagination.

A detailed documentation can be found [here](http://164.132.169.19:8001/redoc).

### Trading
The Trading API Endpoint allows querying the trading volume per wallet. A distinction is made between Maker and Taker volume. The trading fees already paid or earned can also be queried.

### Price
A small API endpoint that should be helpful to quickly get the current exchange rates for the well-known Tradehub Coins. Furthermore, the retrieval of historical exchange rates with multiple formatting is possible.  