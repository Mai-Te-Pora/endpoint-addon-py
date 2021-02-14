from typing import Optional, List
from utils import request_get
import os

COINGECKO_BASE_URI = os.getenv("BASE_URI_COINGECKO") or "https://api.coingecko.com/api/v3"


def get_historical_price(coin: str, vs_currency: str, from_epoch: int, to_epoch: int) -> List:
    return request_get(path=f"/coins/{coin}/market_chart/range", base_uri=COINGECKO_BASE_URI, params={
        "vs_currency": vs_currency,
        "from": from_epoch,
        "to": to_epoch
    })


def get_price(coins: List[str], vs_currencies: List[str]) -> List:
    return request_get(path="/simple/price", base_uri=COINGECKO_BASE_URI, params={
        "ids": ",".join(coins),
        "vs_currencies": ",".join(vs_currencies)
    })