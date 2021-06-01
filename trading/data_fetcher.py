import asyncio
import time
from decimal import Decimal
from typing import List

from aiohttp import ClientSession
from requests import HTTPError
import iso8601
from utils.postgresql import connect, config
from price.data_fetcher import get_historic_price

SQL_CREATE_TABLE = '''CREATE TABLE IF NOT EXISTS public.trades
(
    id bigint NOT NULL,
    "time" timestamp with time zone NOT NULL,
    taker character(43) NOT NULL,
    maker character(43) NOT NULL,
    buy boolean NOT NULL,
    taker_fee numeric NOT NULL,
    maker_fee numeric NOT NULL,
    market character(15) NOT NULL,
    price numeric NOT NULL,
    quantity numeric NOT NULL,
    height integer NOT NULL,
    volume numeric,
    taker_fee_usd numeric,
    maker_fee_usd numeric,
    CONSTRAINT trades_pkey PRIMARY KEY (id)
)'''

HOST = "http://164.132.169.19:5001"

MARKETS = {}

async def get_markets():
    async with ClientSession() as session:
        url = f"{HOST}/get_markets"
        result = await session.request(method='GET', url=url)
        data = await result.json()
        print(data)
        return data


async def update_markets():
    global MARKETS
    data = await get_markets()
    markets = {}
    for market in data:
        ticker = market["name"]
        markets[ticker] = market
    MARKETS = markets


def create_tables(db_config):
    global SQL_CREATE_TABLE
    with connect(db_config) as connection:
        cur = connection.cursor()

        cur.execute(SQL_CREATE_TABLE)

        connection.commit()

        cur.close()


def get_max_trade_id_and_count(db_config):
    with connect(db_config) as connection:
        cur = connection.cursor()

        cur.execute("SELECT MAX(id), COUNT(1) FROM public.trades;")

        result = cur.fetchone()

        cur.close()

        if result[0] and result[1]:
            return result[0], result[1]
    return 0, 0


def calculate_volume_and_fees(db_config, trade: dict):
    global MARKETS
    ticker: str = trade["market"]
    if ticker not in MARKETS:
        raise RuntimeError(f"No market found for {ticker}")

    market = MARKETS[ticker]

    timestamp = trade["block_created_at"]

    taker_fee_denom = trade["taker_fee_denom"]
    taker_fee_amount = trade["taker_fee_amount"]
    taker_fee_usd = "0"
    taker_price = None
    if taker_fee_amount != "0":
        utc_time, taker_price = get_historic_price(db_config, taker_fee_denom, timestamp)
        if taker_price:
            taker_fee_usd = f"{Decimal(taker_fee_amount) * taker_price:.4f}"

    maker_fee_denom = trade["maker_fee_denom"]
    maker_fee_amount = trade["maker_fee_amount"]
    maker_fee_usd = "0"
    if maker_fee_amount != "0":
        if maker_fee_amount == taker_fee_amount:
            maker_fee_usd = taker_fee_usd
        else:
            if taker_fee_denom == maker_fee_denom and taker_price:
                maker_price = taker_price
            else:
                utc_time, maker_price = get_historic_price(db_config, maker_fee_denom, timestamp)

            if maker_price:
                maker_fee_usd = f"{Decimal(maker_fee_amount) * maker_price:.4f}"

    qty_denom = market["base"]
    volume = "0"
    quantity = trade["quantity"]
    utc_time, qty_price = get_historic_price(db_config, qty_denom, timestamp)
    if qty_price:
        volume = f"{Decimal(quantity) * qty_price:.4f}"

    return volume, taker_fee_usd, maker_fee_usd


def insert_trades(db_config: dict, trades: List[dict], highest_db_id: int):
    sql_trades = []
    for trade in trades:
        height: int = int(trade["id"])
        if height <= highest_db_id:
            continue

        volume, taker_fee, maker_fee = calculate_volume_and_fees(db_config, trade)

        timestamp = trade["block_created_at"]

        sql_trades.append(
            (
                trade["id"],
                f"timestamp '{timestamp}'",
                f"'{trade['taker_address']}'",
                f"'{trade['maker_address']}'",
                "true" if trade["taker_side"] == "buy" else "false",
                trade["taker_fee_amount"],
                trade["maker_fee_amount"],
                f"'{trade['market']}'",
                trade["price"],
                trade["quantity"],
                trade["block_height"],
                volume,
                taker_fee,
                maker_fee
            )
        )

    if not sql_trades:
        return

    with connect(db_config) as connection:

        cur = connection.cursor()

        insert_str = ",".join([f"({','.join(sql_trade)})" for sql_trade in sql_trades])
        cur.execute(f"INSERT INTO public.trades(id, time, taker, maker, buy, taker_fee, maker_fee, market, price, quantity, height, volume, taker_fee_usd, maker_fee_usd) VALUES {insert_str}")

        connection.commit()

        cur.close()


async def get_trades(after_id, before_id, session):
    """Get book details using Google Books API (asynchronously)"""
    url = f"{HOST}/get_trades"
    try:
        response = await session.request(method='GET', url=url, params={"before_id": before_id, "after_id": after_id})
        response.raise_for_status()
        print(f"Response status ({url} {after_id}-{before_id}): {response.status}")
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error ocurred: {err}")
    response_json = await response.json()
    return response_json


async def fast_data_fetch(start_id, result, session):
    """Wrapper for running program in an asynchronous manner"""
    try:
        response = await get_trades(start_id, start_id+201, session)
        result += response
    except Exception as err:
        print(f"Exception occured: {err}")
        pass


async def main():
    db_config = config("trading/database.ini")
    create_tables(db_config)
    max_parallel_requests = 100
    parallel_requests = 1
    await update_markets()
    while True:
        highest_db_id, count = get_max_trade_id_and_count(db_config)
        print(f"[{count}]Highest Trade ID in database: {highest_db_id}")
        result = []
        start_time = time.time()
        print(f"Start requesting with {parallel_requests} parallel requests")
        async with ClientSession() as session:
            await asyncio.gather(*[fast_data_fetch(highest_db_id+i*200, result, session) for i in range(parallel_requests)])
        duration = time.time() - start_time
        print(f"Fetching took took {duration:.3}s")
        start_time = time.time()
        insert_trades(db_config, result, highest_db_id)
        duration = time.time() - start_time
        print(f"Inserting took {duration:.3}s")
        parallel_requests = min(int((len(result) / 200) * 2)+1, max_parallel_requests)
        if len(result) < 200:
            time.sleep(2)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
