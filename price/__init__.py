import json
import time
from typing import Optional
from utils import load_file, get_file_logger, epoch_seconds_to_local_timestamp, save_file, create_sub_dir, \
    files_in_path, timestamp_to_epoch_seconds, path_parts_to_abs_path, directory_exists, file_exists
from utils.coingecko import get_historical_price, get_price
from utils.exception import RequestTimedOut
from price.coins import COINS
import os
import urllib3
# disable coingecko warnings
urllib3.disable_warnings()

# Shared memory dict for main and sub thread.
SHARED_MEMORY_DICT = {
    "current": {
        "prices": {},
        "epoch_seconds": "0",
    },
}


DATABASE_PATH = ["..", "database", "price"]

START_EPOCH = os.getenv("START_EPOCH") or 1596240000  # 2020-08-01 00:00:00 UTC+00:00 = 1596240000
TIME_WINDOW = os.getenv("TIME_WINDOW") or 3600  # 1H = 3600
VS_CURRENCY = os.getenv("VS_CURRENCY") or "usd"
REQUESTS_PER_MINUTE = os.getenv("REQUESTS_PER_MINUTE") or 100
MERGE_BATCH_SIZE = os.getenv("MERGE_BATCH_SIZE") or 100

DENOM_TO_NAME = {}
NAME_TO_DENOMS = {}

LOGGER = get_file_logger("price")


async def api_get_current_price(denom: str, vs_currency: str):
    print(SHARED_MEMORY_DICT)
    if denom not in SHARED_MEMORY_DICT["current"]["prices"].keys():
        raise IndexError(f"Denom '{denom}' is not known!")

    if vs_currency not in SHARED_MEMORY_DICT["current"]["prices"][denom].keys():
        raise IndexError(f"Vs currency '{vs_currency}' is not known!")

    return SHARED_MEMORY_DICT["current"]["prices"][denom][vs_currency], SHARED_MEMORY_DICT["current"]["epoch_seconds"]


async def api_get_historic_price(denom: str, epoch: float):
    if denom not in DENOM_TO_NAME.keys():
        raise IndexError(f"No historical data found for denom '{denom}.'")

    name: str = DENOM_TO_NAME[denom]
    path: str = path_parts_to_abs_path(DATABASE_PATH + [name])

    if not directory_exists(path):
        raise NotADirectoryError(f"No historical data available for denom '{denom}.'")

    files = files_in_path(path)

    start_epoch = 0
    end_epoch = 0

    for file in files:
        if file.endswith(".json"):
            _, filename = os.path.split(file)
            start_epoch, end_epoch = filename.split("-")
            start_epoch = int(start_epoch)
            end_epoch = int(end_epoch.split(".")[0])
            if start_epoch <= epoch < end_epoch:
                break

    filename: str = f"{start_epoch}-{end_epoch}.json"
    path: str = path_parts_to_abs_path(DATABASE_PATH + [name, filename])

    if not file_exists(path):
        raise FileNotFoundError(f"No historical data available for epoch '{epoch}'")

    with open(path, "r") as file:
        data = json.loads(file.read())

    epoch: int = int(epoch * 1000)

    price, cur_epoch = await api_get_current_price(denom, "usd")
    data.append([int(float(cur_epoch)*1000), float(price)])

    historic_price = sorted(data, key = lambda key: abs(key[0] - epoch))[0]

    return f"{historic_price[1]}", f"{historic_price[0]/1000}"


async def api_get_historic_price_timestamp(denom: str, timestamp: str):
    try:
        epoch: float = timestamp_to_epoch_seconds(timestamp)
    except:
        raise ValueError(f"Unable to parse timestamp '{timestamp}'")

    return await api_get_historic_price(denom, epoch)


def main_current_price():
    global SHARED_MEMORY_DICT
    coins = list(NAME_TO_DENOMS.keys())
    vs_currencies = [VS_CURRENCY, "eur", "btc", "eth"]

    while True:
        prices = get_price(coins, vs_currencies)
        denom_price = {}
        for name in prices:
            denoms = NAME_TO_DENOMS[name]
            for denom in denoms:
                denom_price[denom] = {}
                for vs_currency in prices[name]:
                    denom_price[denom][vs_currency] = "%.8f" % prices[name][vs_currency]
        SHARED_MEMORY_DICT["current"]["prices"] = denom_price
        SHARED_MEMORY_DICT["current"]["epoch_seconds"] = f"{time.time()}"
        time.sleep(60)


def main_history_data():

    for name in NAME_TO_DENOMS.keys():
        path = create_sub_dir(DATABASE_PATH + [name])
        files = files_in_path(path)
        highest_epoch = START_EPOCH
        for file in files:
            if file.endswith(".json"):
                _, filename = os.path.split(file)
                start_epoch, _ = filename.split("-")
                start_epoch = int(start_epoch)
                if start_epoch > highest_epoch:
                    highest_epoch = start_epoch

        load_prices_til_now(name, highest_epoch)


def load_prices_til_now(coin: str, start_time: Optional[float] = None):
    global VS_CURRENCY
    start_time = start_time or START_EPOCH
    end_time = start_time+TIME_WINDOW * 24 * 90
    prices = []
    LOGGER.info(f"Start with coin: {coin} from {epoch_seconds_to_local_timestamp(start_time)}")
    while start_time < time.time():
        try:
            data = get_historical_price(coin, VS_CURRENCY, start_time, end_time)
        except RequestTimedOut:
            LOGGER.warning(f"Request timed out, wait 30sec and try again at {start_time}-{end_time}")
            time.sleep(30)
            continue
        prices += data["prices"]
        start_time = end_time
        end_time = start_time+TIME_WINDOW * 24 * 90
        time.sleep(60/REQUESTS_PER_MINUTE)

    grouped_by = {}

    epoch_start = START_EPOCH
    for price in prices:
        index = int((int(price[0]/1000) - START_EPOCH) / TIME_WINDOW)
        from_index = int(index / MERGE_BATCH_SIZE) * MERGE_BATCH_SIZE
        to_index = from_index + MERGE_BATCH_SIZE

        epoch_start = START_EPOCH + from_index * TIME_WINDOW
        epoch_end = START_EPOCH + to_index * TIME_WINDOW

        key = f"{epoch_start}-{epoch_end}"
        if key not in grouped_by.keys():
            grouped_by[key] = []
        grouped_by[key].append(price)

    path = create_sub_dir(DATABASE_PATH + [coin])

    for key in grouped_by.keys():
        save_file(path, f"{key}.json", json.dumps(grouped_by[key], indent=4))

    return epoch_start


def load_predefined_coins():
    global DENOM_TO_NAME, NAME_TO_DENOMS, COINS
    """coins = load_file("coins.json")
    if not coins:
        raise RuntimeError("Could not load the initial coin list! coins.json is missing")

    try:
        coins = json.loads(coins)
    except json.JSONDecodeError:
        LOGGER.warning("Could not parse coins.json")
        return"""

    coins = COINS

    # make first a local dict and change reference
    name_to_denoms = {}
    for denom in coins.keys():
        name = coins[denom]
        if name not in name_to_denoms.keys():
            name_to_denoms[name] = []
        name_to_denoms[name].append(denom)

    DENOM_TO_NAME = coins
    NAME_TO_DENOMS = name_to_denoms


def create_tables(db_config):
    pass