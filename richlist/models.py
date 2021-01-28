from typing import Dict, List, Union, Optional
from pydantic import BaseModel, Field


class RichListError(BaseModel):
    error: str = Field(..., description="Description off occurred error.", example="Requested denom 'moon_poon_coin' does not exit(yet).")


class RichListGetDenoms(BaseModel):
    denoms: List[str] = ["swth", "usdc1", "..."]


class RichListBalance(BaseModel):
    available: str = Field(..., description="Available balance.", example="2194864.90202575")
    staking: str = Field(..., description="Staked balance.", example="113718080.00000255")
    unbonding: str = Field(..., description="Unbonding balance.", example="0.00000000")
    rewards: str = Field(..., description="Outstanding delegation rewards.", example="401345.66815705")
    commission: str = Field(..., description="Outstanding validator commissions.", example="0.0")
    orders: str = Field(..., description="Balance in open spot orders.", example="0.00000000")
    positions: str = Field(..., description="Balance in open future positions.", example="0.00000000")
    total: str = Field(..., description="Total balance, which is the sum off all sub balances.", example="116314290.57018535")


class RichListWallet(BaseModel):
    address: str = Field(..., description="Official 'swth1' address", example="swth1uv20wttn7nvy65m5368zcgrqz99te88z3xa7f8")
    last_seen_time: str = Field(..., description="Last seen local sentry timestamp.", example="2021-01-25T10:17:42.384259+01:00")
    last_seen_height: int = Field(..., description="Last seen block height.", example=6733065)
    last_checked_time: str = Field(..., description="Last updated local sentry timestamp.", example="2021-01-28T12:13:18.203613+01:00")
    last_checked_height: int = Field(..., description="Last updated block height.", example=6855507)
    username: Optional[str] = Field(None, description="Username if set, Moniker if wallet is from Validator or AMM Name if wallet is Automated Market Maker.", example="Switcheo Wallet #1")
    validator: Optional[str] = Field(None, description="Operator address if wallet is from Validator.")
    balance: RichListBalance


class RichListTop(BaseModel):
    denom: str = Field(description="Requested denom.",  example="swth")
    total: int = Field(description="Total wallets holding the requested denom.",  example=1972)
    total_subset: int = Field(description="Total wallets holding the requested denom after applying filters.",  example=10)
    limit: int = Field(description="Parameter limiting the result",  example=10)
    offset: int = Field(description="Parameter offsetting the result",  example=0)
    wallets: Optional[List[RichListWallet]] = Field(description="Sorted list with wallets. Sort by 'total'")