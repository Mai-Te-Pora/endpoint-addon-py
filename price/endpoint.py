from fastapi import APIRouter, Query, Path
from fastapi.responses import JSONResponse
from price import api_get_current_price, api_get_historic_price, api_get_historic_price_timestamp

# FAST API router
API_ROUTER = APIRouter()


@API_ROUTER.get("/{denom}", response_class=JSONResponse)
async def get_price_vs_currency(denom: str, vs_currency: str = "usd"):

    price = await api_get_current_price(denom, vs_currency)

    return JSONResponse({
        "denom": denom,
        "vs_currency": vs_currency,
        "price": price
    })


@API_ROUTER.get("/historic/{denom}", response_class=JSONResponse)
async def get_historic_price(denom: str, epoch: int):
    price, epoch = await api_get_historic_price(denom, epoch)

    return JSONResponse({
        "denom": denom,
        "vs_currency": "usd",
        "price": price,
        "epoch": epoch
    })


@API_ROUTER.get("/historic/{denom}/{timestamp}", response_class=JSONResponse)
async def get_historic_price(denom: str, timestamp: str):
    price, epoch = await api_get_historic_price_timestamp(denom, timestamp)

    return JSONResponse({
        "denom": denom,
        "vs_currency": "usd",
        "price": price,
        "epoch": epoch
    })

