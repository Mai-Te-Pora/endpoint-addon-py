
import asyncio
import json
import time
import requests

from aiohttp import ClientSession
from aiohttp.web_exceptions import HTTPError

PRICE_URL = "http://164.132.169.19:8002/price/{}?vs_currency={}"
MARKETS = [
    "wbtc1_usdc1",
    "swth_usdc1",
    "swth_eth1",
    "swth_usdc1",
    "eth1_wbtc1"
]

VS_CONVERT = {
    "wbtc1": "btc",
    "eth1": "eth",
    "usdc1": "usd"
}


async def get_price_async(market, session):
    """Get book details using Google Books API (asynchronously)"""
    quote, base = market.split("_")
    if base in VS_CONVERT.keys():
        base = VS_CONVERT[base]
    url = PRICE_URL.format(quote, base)
    try:
        response = await session.request(method='GET', url=url)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error ocurred: {err}")
    return response.json()


def get_price_sync(market, session):
    """Get book details using Google Books API (asynchronously)"""
    quote, base = market.split("_")
    if base in VS_CONVERT.keys():
        base = VS_CONVERT[base]
    url = PRICE_URL.format(quote, base)
    try:
        response = session.request(method='GET', url=url)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error ocurred: {err}")
    return response.json()



async def run_program(isbn, session):
    """Wrapper for running program in an asynchronous manner"""
    try:
        response = await get_price_async(isbn, session)
    except Exception as err:
        print(f"Exception occured: {err}")
        pass

def run_sync_program(market, session):
    """Wrapper for running program in an asynchronous manner"""
    try:
        response = get_price_sync(market, session)
        print(response)
    except Exception as err:
        print(f"Exception occured: {err}")
        pass


async def async_main():

    async with ClientSession() as session:
        await asyncio.gather(*[run_program(isbn, session) for isbn in MARKETS])


def sync_main():
    for market in MARKETS:
        run_sync_program(market, requests.session())


if __name__ == '__main__':
    start = time.time()
    asyncio.get_event_loop().run_until_complete(async_main())
    end = time.time()
    print(f"Duration: {(end-start)*1000:.3f} ms")
    start = time.time()
    sync_main()
    end = time.time()
    print(f"Duration: {(end-start)*1000:.3f} ms")
