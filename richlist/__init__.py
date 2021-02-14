import json
import time
import os
from typing import Optional, Union
from utils import create_sub_dir, load_files, get_file_logger, save_file
from utils.rest import (get_blocks,
                        get_all_validators,
                        get_balance,
                        get_profile,
                        get_tokens,
                        get_liquidity_pools)
from utils.cosmos import (get_validator_delegations,
                          get_delegator_delegations,
                          get_delegator_unbonding_delegations,
                          get_delegator_distribution,
                          get_validator_distribution)
from utils.exception import DelegationDoesNotExist, ValidatorDoesNotExist, RequestTimedOut, NodeIsCatchingUp
import richlist.endpoint

# DATABASE PATH as list to allow windows too.
DATABASE_PATH = ["..", "database", "richlist", "wallet"]

# Seconds between each block fetch
SECONDS_BETWEEN_BLOCK_FETCH = float(os.getenv("SECONDS_BETWEEN_BLOCK_FETCH")) if os.getenv("SECONDS_BETWEEN_BLOCK_FETCH") else 10
# Max block height spread between each wallet full update
MAX_BLOCK_SPREAD_UPDATE_WALLET = float(os.getenv("MAX_BLOCK_SPREAD_UPDATE_WALLET")) if os.getenv("MAX_BLOCK_SPREAD_UPDATE_WALLET") else 2000
# Max block height spread between for fetching wallet sources
MAX_BLOCK_SPREAD_FETCH_SOURCES = float(os.getenv("MAX_BLOCK_SPREAD_FETCH_SOURCES")) if os.getenv("MAX_BLOCK_SPREAD_FETCH_SOURCES") else 5000

# In memory storage for currently loaded wallets
WALLETS = {}
# In memory storage for token information(used by staking)
TOKENS = {}
# BLOCK dict of last fetched block
BLOCK = {}


# Terminal log level
LOG_LEVEL_TERMINAL = os.getenv("LOG_LEVEL_TERMINAL") or "INFO"
# File log level
LOG_LEVEL_FILE = os.getenv("LOG_LEVEL_FILE") or "INFO"
# Global richlist logger
LOGGER = get_file_logger("richlist", terminal_log_level=LOG_LEVEL_TERMINAL, file_log_level=LOG_LEVEL_FILE)


def update_richlist():
    """
    Main program for rich list. This function is threaded.
    :return: None
    """
    # get global database path and other settings
    global DATABASE_PATH, SECONDS_BETWEEN_BLOCK_FETCH, MAX_BLOCK_SPREAD_FETCH_SOURCES
    # create database directories if not created yet
    # returns the abs path to directory
    wallet_db: str = create_sub_dir(DATABASE_PATH)
    # load wallets from db
    load_wallets(wallet_db)
    # update richlist
    update_rich_list_per_coin()
    # get the lowest checked height of a wallet
    last_full_fetch_height: int = get_last_check_block_height()
    LOGGER.info(f"Loaded {len(WALLETS.keys())} wallets, lowest block height: {last_full_fetch_height}")
    LOGGER.info(f"ENVIRONMENT {LOG_LEVEL_TERMINAL} {LOG_LEVEL_FILE}")
    while True:
        try:
            # get current block
            block: dict = BLOCK
            block_height: int = int(block['block_height'])
            block_time: str = block['time']
            LOGGER.info(f"Current block {block_height} - {block_time}")
            # check if full fetch is required
            if block_height - last_full_fetch_height > MAX_BLOCK_SPREAD_FETCH_SOURCES:
                fetch_wallets_via_validators()
                fetch_amm_wallets()
                last_full_fetch_height = block_height

            # only update wallets with a max block spread to avoid to many IO operations
            update_wallets = []
            for wallet in WALLETS.values():
                difference: int = block_height - wallet["last_checked_height"]
                if difference > MAX_BLOCK_SPREAD_UPDATE_WALLET:
                    update_wallets.append(wallet)
            LOGGER.info(f"Found {len(update_wallets)} wallets to update")
            # start update process
            for i, wallet in enumerate(update_wallets):
                update_wallet(wallet)
                # use latest block infos
                block: dict = BLOCK
                block_height: int = int(block['block_height'])
                block_time: str = block['time']
                wallet["last_checked_height"] = block_height
                wallet["last_checked_time"] = block_time
                save_wallet(wallet_db, wallet)
                LOGGER.info(f"Updated {i+1}/{len(update_wallets)} wallets.")

            # Create a richlist for each coin found if wallets got updated
            if update_wallets:
                update_rich_list_per_coin()

            # wait until repeat
            time.sleep(SECONDS_BETWEEN_BLOCK_FETCH)
        except RequestTimedOut:
            LOGGER.warning(f"Request timed out, wait 30sec and retry.")
            time.sleep(30)
        except NodeIsCatchingUp:
            LOGGER.warning(f"Node is catching up, wait 60sec")
            time.sleep(60)


def update_block_height():
    """
    Threaded function to fetch current block height to enable better last_check_height
    :return:
    """
    global SECONDS_BETWEEN_BLOCK_FETCH, BLOCK
    while True:
        try:
            block: dict = get_blocks(limit=1)[0]
            BLOCK = block
            time.sleep(SECONDS_BETWEEN_BLOCK_FETCH)
        except RequestTimedOut:
            LOGGER.warning(f"Requesting last block timed out, wait 10sec and retry.")
            time.sleep(10)
        except NodeIsCatchingUp:
            LOGGER.warning(f"Node is catching up, wait 60sec")
            time.sleep(60)


def update_rich_list_per_coin():
    """
    Update the richlist per coin using the global wallet dict.
    :return: None
    """
    # get global data
    # SHARED_MEMORY_DICT is from the API endpoint imported to share between main and sub thread.
    global TOKENS, WALLETS

    # copy all wallets so the update process does not make problems if endpoint is requested
    wallets = [wallet.copy() for wallet in WALLETS.values()]

    wallets_per_coin = {}

    # build dict for each coin containing all wallets owning this coin
    for wallet in wallets:
        for coin in wallet["balance"].keys():
            if coin not in wallets_per_coin.keys():
                wallets_per_coin[coin] = []

            wallets_per_coin[coin].append(wallet)

    # save sorted dict to shared memory
    for coin in wallets_per_coin:
        richlist.endpoint.SHARED_MEMORY_DICT[coin] = sorted(wallets_per_coin[coin], key=lambda entry: float(entry["balance"][coin]["total"]), reverse=True)
        LOGGER.info(f"Updated richlist for coin '{coin}'. Wallets: {len(richlist.endpoint.SHARED_MEMORY_DICT[coin])}")


def load_wallets(path: str) -> None:
    """
    Load all wallets into global WALLETS and return the lowest checked block height
    :param path:
    :return:
    """
    for data in load_files(path, ".json"):
        wallet: dict = json.loads(data)
        WALLETS[wallet["address"]] = wallet
        LOGGER.info(f"Loaded wallet: {wallet['address']}")


def save_wallet(path: str, wallet: dict) -> None:
    """
    Save wallet to the defined path. The fill will be saved as .json.
    :param path:
    :param wallet:
    :return:
    """
    data: str = json.dumps(wallet, indent=4)
    save_file(path, f"{wallet['address']}.json", data)


def get_last_check_block_height() -> int:
    """
    Sorts the wallets by last checked block height and returns the lowest height. If no wallets are available
    return 0.
    :return: last checked height or 0.
    """
    sorted_by_block_height: list = sorted(WALLETS.values(), key=lambda entry: entry["last_checked_height"])
    if sorted_by_block_height:
        return sorted_by_block_height[0]["last_checked_height"]
    return 0


def get_wallet(swth_address: str):
    """
    Get a wallet from global storage. If requested wallet does not exist return new dict and add to storage.
    :param swth_address: wallet address staring with 'swth1' or 'tswth1'
    :return: wallet as editable dict
    """
    if swth_address not in WALLETS.keys():
        WALLETS[swth_address] = {
            "address": swth_address,
            "last_seen_time": None,
            "last_seen_height": 0,
            "last_checked_time": None,
            "last_checked_height": 0,
            "username": None,
            "validator": None,
            "balance": {

            }
        }
    return WALLETS[swth_address]


def set_wallet_balance(wallet: dict,
                       denom: str,
                       available: Optional[float] = None,
                       staking: Optional[float] = None,
                       unbonding: Optional[float] = None,
                       rewards: Optional[float] = None,
                       commission: Optional[float] = None,
                       orders: Optional[float] = None,
                       positions: Optional[float] = None):
    """
    Set the balance of a specific denom. Will automatically trigger an total update for the denom.

    :param wallet: wallet as dict.
    :param denom: the asset to update.
    :param available: Available balance.
    :param staking: Balance looked in staking.
    :param unbonding: Balanced looked in unbonding.
    :param rewards: Outstanding delegation rewards.
    :param commission: Outstanding validator commissions.
    :param orders: Balance in open orders.
    :param positions: Balance in open positions.
    :return: None
    """
    if denom not in wallet["balance"].keys():
        wallet["balance"][denom] = {
            "available": "0.0",
            "staking": "0.0",
            "unbonding": "0.0",
            "rewards": "0.0",
            "commission": "0.0",
            "orders": "0.0",
            "positions": "0.0",
            "total": "0.0"
        }

    if available is not None:
        wallet["balance"][denom]["available"] = add_floats_to_str(denom, available, 0.0)

    if staking is not None:
        wallet["balance"][denom]["staking"] = add_floats_to_str(denom, staking, 0.0)

    if unbonding is not None:
        wallet["balance"][denom]["unbonding"] = add_floats_to_str(denom, unbonding, 0.0)

    if rewards is not None:
        wallet["balance"][denom]["rewards"] = add_floats_to_str(denom, rewards, 0.0)

    if commission is not None:
        wallet["balance"][denom]["commission"] = add_floats_to_str(denom, commission, 0.0)

    if orders is not None:
        wallet["balance"][denom]["orders"] = add_floats_to_str(denom, orders, 0.0)

    if positions is not None:
        wallet["balance"][denom]["positions"] = add_floats_to_str(denom, positions, 0.0)

    # update total
    keys = list(wallet["balance"][denom].keys())
    keys.remove("total")
    total: str = "0.0"
    for key in keys:
        total = add_floats_to_str(denom, total, wallet["balance"][denom][key])
    wallet["balance"][denom]["total"] = total


def fetch_wallets_via_validators() -> None:
    """
    Fetch delegator and validator wallets using the staking endpoints. Simplest and fastest way to get wallets. Will
    create wallets in global storage.

    :return: None
    """
    json_validators = get_all_validators()
    LOGGER.info(f"Found {len(json_validators)} Validators in total")
    for json_val in json_validators:
        wallet_address = json_val["WalletAddress"]
        moniker = json_val["Description"]["moniker"]
        swthval_address = json_val["OperatorAddress"]
        validator = get_wallet(wallet_address)
        # update the validator wallet and add operator address and moniker as username
        validator["validator"] = swthval_address
        validator["username"] = moniker
        delegations = get_validator_delegations(swthval_address)["result"]
        LOGGER.info(f"Validator {moniker} with wallet {wallet_address} has {len(delegations)} delegators")
        for delegator in delegations:
            swth_address = delegator["delegator_address"]
            # use get wallet to initialize wallet if not existed yet
            get_wallet(swth_address)
    LOGGER.info(f"Total fetched wallets via staking: {len(WALLETS.values())}")


def fetch_amm_wallets() -> None:
    """
    Fetch liquidity pools, their AMM wallets and update the user name to pool name.
    :return: None
    """
    amm_wallets = get_liquidity_pools()
    for pool in amm_wallets:
        wallet: dict = get_wallet(pool["pool_address"])
        wallet["username"] = pool["name"]
        LOGGER.info(f"AMM Pool {wallet['username']} fetched with wallet {wallet['address']}")


def update_wallet(wallet: dict):
    """
    Updating procedure for a wallet.
    :param wallet: wallet to update
    :return: None
    """
    try:
        LOGGER.info(f"Start updating {wallet['address']}")

        # Rest balance to avoid staking/unbonding not to be displayed correct
        wallet["balance"] = {}

        # update currently balances
        update_wallet_balance(wallet)

        # update wallet delegations
        update_delegations(wallet)

        # update wallet infos
        update_wallet_info(wallet)

        # update wallet unbonding delegations
        update_delegator_unbonding_delegation(wallet)
        # check if wallet is validator and fetch rewards + commission or only rewards
        if wallet["validator"]:
            update_validator_distribution(wallet)
        else:
            update_delegator_distribution(wallet)

    except RequestTimedOut:
        LOGGER.info(f"Request timed out while updating delegator: {wallet['address']}. Wait 30sec and continue")
        time.sleep(30)
        update_wallet(wallet)
    except (DelegationDoesNotExist, ValidatorDoesNotExist):
        # Old unbonded validators can have no delegations which causes an API error. Remove them as validator and use
        # the normal delegator endpoint
        LOGGER.info(f"Validator {wallet['username']} has no more delegations. Treat them as usual wallet.")
        wallet["validator"] = None
        wallet["username"] = None
        update_wallet(wallet)
    except NodeIsCatchingUp:
        # sadly happens to often
        LOGGER.info(f"Node is catching up while updating wallet: {wallet['address']}. Wait 60sec and continue")
        time.sleep(60)
        update_wallet(wallet)


def update_wallet_balance(wallet: dict) -> None:
    """
    Update currently available, in orders and positions balance.
    :param wallet: wallet to update
    :return: None
    """
    # get sub dict to access faster
    balance = get_balance(wallet["address"])

    if balance:
        for coin in balance.values():
            denom: str = coin["denom"]
            available: float = float(coin["available"])
            order: float = float(coin["order"])
            position: float = float(coin["position"])
            set_wallet_balance(wallet, denom, available=available, orders=order, positions=position)


def update_delegations(wallet: dict) -> None:
    """
    Update currently delegated amounts.
    :param wallet: wallet to update
    :return: None
    """

    delegations: dict = get_delegator_delegations(wallet["address"])
    totals: dict = {}
    for delegation_json in delegations["result"]:
        denom: str = delegation_json["balance"]["denom"]
        if denom not in totals.keys():
            totals[denom] = 0.0
        amount: float = big_float_to_real_float(denom, float(delegation_json["balance"]["amount"]))
        totals[denom] += amount

    for denom in totals.keys():
        set_wallet_balance(wallet, denom, staking=totals[denom])


def update_wallet_info(wallet: dict) -> None:
    """
    Update profile information like username, last seen time and height.
    :param wallet: wallet to update
    :return: None
    """

    info = get_profile(wallet["address"])

    if info["username"]:
        wallet["username"] = info["username"]

    wallet["last_seen_height"] = int(info["last_seen_block"])
    wallet["last_seen_time"] = info["last_seen_time"]


def update_delegator_unbonding_delegation(wallet: dict) -> None:
    """
    Update unbonding delegations.
    :param wallet: wallet to update
    :return: None
    """
    unbonding = get_delegator_unbonding_delegations(wallet["address"])
    total: float = 0.0
    for unbond_process in unbonding["result"]:
        for i in range(len(unbond_process["entries"])):
            # TODO no info about denom in response
            denom: str = "swth"
            amount: float = big_float_to_real_float(denom, float(unbond_process["entries"][i]["balance"]))
            total += amount
    set_wallet_balance(wallet, denom="swth", unbonding=total)


def update_validator_distribution(wallet: dict) -> None:
    """
    Update validator outstanding self staking rewards and the commissions.
    :param wallet: wallet to update
    :return: None
    """
    commission = get_validator_distribution(wallet["validator"])
    if "result" in commission.keys():
        if commission["result"]:
            if "self_bond_rewards" in commission["result"].keys():
                for token in commission["result"]["self_bond_rewards"]:
                    denom: str = token["denom"]
                    amount: float = big_float_to_real_float(denom, float(token["amount"]))
                    set_wallet_balance(wallet, denom, rewards=amount)
            if "val_commission" in commission["result"].keys():
                for token in commission["result"]["val_commission"]:
                    denom: str = token["denom"]
                    amount: float = big_float_to_real_float(denom, float(token["amount"]))
                    set_wallet_balance(wallet, denom, commission=amount)


def update_delegator_distribution(wallet: dict) -> None:
    """
    Update normal wallet outstanding rewards.
    :param wallet: wallet to update
    :return: None
    """
    rewards = get_delegator_distribution(wallet["address"])
    if rewards["result"]["total"]:
        for denom_dict in rewards["result"]["total"]:
            denom: str = denom_dict["denom"]
            amount: float = big_float_to_real_float(denom, float(denom_dict["amount"]))
            set_wallet_balance(wallet, denom, rewards=amount)


def add_floats_to_str(denom: str, number_1: Union[str, float], number_2: Union[str, float]) -> str:
    """
    Add two floats to produce a float as string with the decimal precision of the denom.
    This is a helper function of set_wallet_balance.

    :param denom: denom of the asset
    :param number_1: float or string
    :param number_2: float or string
    :return: string
    """
    if isinstance(number_1, str):
        number_1: float = float(number_1)

    if isinstance(number_2, str):
        number_2: float = float(number_2)

    number: float = number_1 + number_2
    decimals: int = get_denom_decimals(denom)
    return ("%%.%df" % decimals) % number


def update_tokens() -> None:
    """
    Update global token information
    :return: None
    """
    global TOKENS
    response = get_tokens()
    for token in response:
        asset: str = token["denom"]
        TOKENS[asset] = token


def get_denom_decimals(denom: str) -> int:
    """
    Get denom decimals.
    :param denom: denom of the assest
    :return: decimals as int
    """
    global TOKENS
    # check if tokens are not fetched yet
    if not TOKENS:
        # request tokens
        update_tokens()
        if not TOKENS:
            raise RuntimeError(f"Could not find token infos in general even after refetching!")
    if denom not in TOKENS.keys():
        update_tokens()
        if denom not in TOKENS.keys():
            raise RuntimeError(f"Could not find token info about {denom} even after refetching!")

    return TOKENS[denom]["decimals"]


def big_float_to_real_float(denom: str, amount: float) -> float:
    """
    Small helper function to convert cosmos amounts to human readable format.
    :param denom: denom of the asset
    :param amount: cosmos amount
    :return: amount as float
    """
    decimals = get_denom_decimals(denom)
    return amount / pow(10, decimals)
