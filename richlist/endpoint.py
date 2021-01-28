from fastapi import APIRouter, Query, Path
from fastapi.responses import JSONResponse
from richlist.models import RichListGetDenoms, RichListTop, RichListError

SHARED_MEMORY_DICT = {}

API_ROUTER = APIRouter()


@API_ROUTER.get("/get_denoms", response_class=JSONResponse, response_model=RichListGetDenoms)
async def get_denoms():
    data = {
        "denoms": list(SHARED_MEMORY_DICT.keys())
    }
    return JSONResponse(data, status_code=200)


@API_ROUTER.get("/{denom}/top", response_class=JSONResponse, response_model=RichListTop, responses={404: {"model": RichListError}})
async def get_rich_list(denom: str = Path("swth", min_length=3, description="Requested denom, see '/get_denoms'."),
                        limit: int = Query(10, ge=1, le=100, description="Limit the response result."),
                        offset: int = Query(0, ge=0, description="Request result with offset.")):

    if denom not in SHARED_MEMORY_DICT.keys():
        data = {
            "error": f"Denom '{denom}' is not known"
        }
        return JSONResponse(data, status_code=404)

    sorted_wallets = SHARED_MEMORY_DICT[denom]

    subset_wallets = [wallet.copy() for wallet in sorted_wallets[offset:offset+limit]]

    for wallet in subset_wallets:
        wallet["balance"] = wallet["balance"][denom]

    data = {
        "denom": denom,
        "total": len(sorted_wallets),
        "total_subset": len(subset_wallets),
        "limit": limit,
        "offset": offset,
        "wallets": subset_wallets
    }
    return JSONResponse(data, status_code=200)

