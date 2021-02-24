from typing import Optional
from utils import request_get
import os

REST_BASE_URI = os.getenv("BASE_URI_REST") or "http://164.132.169.19:5002"


def get_blocks(limit: Optional[int] = 200):
    return request_get("/get_blocks", base_uri=REST_BASE_URI, params={"limit": limit})


def get_all_validators():
    return request_get("/get_all_validators", base_uri=REST_BASE_URI)


def get_balance(address: str):
    return request_get("/get_balance", base_uri=REST_BASE_URI, params={"account": address})


def get_profile(address: str):
    return request_get("/get_profile", base_uri=REST_BASE_URI, params={"account": address})


def get_tokens():
    return request_get("/get_tokens", base_uri=REST_BASE_URI)


def get_liquidity_pools():
    return request_get("/get_liquidity_pools", base_uri=REST_BASE_URI)