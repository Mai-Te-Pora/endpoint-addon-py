import asyncio
import datetime
import time

import requests

import utils
from price.coins import COINS
from utils.postgresql import config, connect
from utils.coingecko import get_historical_price


SQL_CREATE_TABLE_COINGECKO = """CREATE TABLE IF NOT EXISTS public.coingecko
(
    denom varchar NOT NULL,
    id varchar NOT NULL,
    start_from timestamp with time zone DEFAULT '2020-08-14T07:32:27.8567Z',
    PRIMARY KEY (denom)
)"""

SQL_CREATE_TABLE_CONVERSION = """CREATE TABLE IF NOT EXISTS public.conversion
(
    "time" timestamp with time zone NOT NULL,
    denom varchar NOT NULL,
    price numeric NOT NULL,
    PRIMARY KEY ("time")
)"""


SQL_SELECT_BEST_PRICE = """
SELECT time, price
FROM public.conversion 
WHERE denom=%s
ORDER BY ABS(EXTRACT(EPOCH FROM time - timestamp %s)) ASC
LIMIT 1"""

VS_CURRENCIES = "usd"


def get_historic_price(db_config, denom: str, timestamp: str):
    with connect(db_config) as connection:

        cur = connection.cursor()

        cur.execute(SQL_SELECT_BEST_PRICE, (denom, timestamp,))

        result = cur.fetchone()
        if result and result[0]:
            return result
    return None, None


def create_tables(db_config):
    with connect(db_config) as connection:
        cur = connection.cursor()

        cur.execute(SQL_CREATE_TABLE_COINGECKO)

        cur.execute(SQL_CREATE_TABLE_CONVERSION)

        for denom in COINS:
            coingecko_id = COINS[denom]["id"]
            start_from = COINS[denom]["start_from"]
            cur.execute(f"INSERT INTO public.coingecko VALUES ('{denom}', '{coingecko_id}', '{start_from}') ON CONFLICT DO NOTHING")

        connection.commit()

        cur.close()


def select_all_coins(db_config):
    coins = {}
    with connect(db_config) as connection:
        cur = connection.cursor()

        cur.execute("SELECT * FROM public.coingecko")

        result = cur.fetchall()

        cur.close()

        for coin in result:
            coins[coin[0]] = {
                "id": coin[1],
                "start_from": coin[2],
            }
    return coins


def update_start_from(db_config, coins):
    with connect(db_config) as connection:
        cur = connection.cursor()

        for denom in coins:
            cur.execute(f"SELECT time FROM public.conversion WHERE denom='{denom}' ORDER BY 1 DESC LIMIT 1")

            result = cur.fetchone()
            if result and result[0]:
                coins[denom]["start_from"] = result[0]


def insert_prices(db_config, denom, prices):

    insert_strings = []

    for price in prices:
        timestamp = datetime.datetime.fromtimestamp(price[0]/1000, datetime.timezone.utc).isoformat()
        price = price[1]
        insert_strings.append(f"('{timestamp}', '{denom}', {price})")

    with connect(db_config) as connection:
        cur = connection.cursor()

        insert_string = ",".join(insert_strings)

        cur.execute(f"INSERT INTO public.conversion VALUES {insert_string} ON CONFLICT DO NOTHING")

        connection.commit()

        cur.close()


async def main():
    db_config = config("price/database.ini")
    create_tables(db_config)
    while True:
        coins = select_all_coins(db_config)
        update_start_from(db_config, coins)
        print("#####################################################")
        for coin in coins:
            denom = coin
            coingecko_id = coins[coin]["id"]
            start_from: datetime.datetime = coins[coin]["start_from"]
            end_time: datetime.datetime = start_from + datetime.timedelta(days=90)
            from_epoch: int = int(start_from.timestamp())
            to_epoch: int = int(end_time.timestamp())
            print(f"{denom} -> {coingecko_id}: {start_from} ({from_epoch}) -> {end_time} ({to_epoch})")
            try:
                prices = get_historical_price(coingecko_id, VS_CURRENCIES, from_epoch, to_epoch)
                print(len(prices["prices"]))
            except utils.exception.RequestTimedOut:
                print("timed out... try next round")
                continue

            time.sleep(3)
            if prices["prices"]:
                insert_prices(db_config, denom, prices["prices"])

        time.sleep(5)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())