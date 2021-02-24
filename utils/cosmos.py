from utils import request_get
import os

COSMOS_BASE_URI = os.getenv("BASE_URI_COSMOS") or "http://164.132.169.19:1318"


def get_delegator_unbonding_delegations(address: str):
    return request_get(f"/staking/delegators/{address}/unbonding_delegations", base_uri=COSMOS_BASE_URI)


def get_validator_delegations(swthvaloper: str):
    return request_get(f"/staking/validators/{swthvaloper}/delegations", base_uri=COSMOS_BASE_URI)


def get_delegator_delegations(address: str):
    return request_get(f"/staking/delegators/{address}/delegations", base_uri=COSMOS_BASE_URI)


def get_validator_distribution(swthvaloper: str):
    return request_get(f"/distribution/validators/{swthvaloper}", base_uri=COSMOS_BASE_URI)


def get_delegator_distribution(address: str):
    return request_get(f"/distribution/delegators/{address}/rewards", base_uri=COSMOS_BASE_URI)
