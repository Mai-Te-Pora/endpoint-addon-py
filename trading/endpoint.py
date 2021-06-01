from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, Path
from fastapi.responses import JSONResponse
from utils.postgresql import config, connect
from richlist.models import RichListGetDenoms, RichListTop, RichListError


API_ROUTER = APIRouter()


DATABASE_CONFIG = config("trading/database.ini")

SQL_LIMIT = 10000


def db_get_trades(taker_address: Optional[str], maker_address: Optional[str],
                  before_id: Optional[int], after_id: Optional[int],
                  before: Optional[str], after: Optional[str],
                  market: Optional[str]):
    global DATABASE_CONFIG, SQL_LIMIT

    where_clauses = []

    if taker_address:
        where_clauses.append(f"taker='{taker_address}'")

    if maker_address:
        where_clauses.append(f"maker='{maker_address}'")

    if before_id:
        where_clauses.append(f"id<{before_id}")

    if after_id:
        where_clauses.append(f"id>{after_id}")

    if before:
        where_clauses.append(f"time< timestamp '{before}'")

    if after:
        where_clauses.append(f"time > timestamp '{after}'")

    if market:
        where_clauses.append(f"market='{market}'")

    where: str = ""
    if where_clauses:
        where: str = f"WHERE " + " AND ".join(where_clauses)

    query_count: str = f"SELECT COUNT(1) FROM public.trades {where}"

    query: str = f"SELECT * FROM public.trades {where} LIMIT {SQL_LIMIT}"
    print(query)
    with connect(DATABASE_CONFIG) as conn:
        cur = conn.cursor()

        cur.execute(query_count)

        count = cur.fetchone()[0]

        if count > SQL_LIMIT:
            return [], count

        cur.execute(query)

        data = cur.fetchall()

        cur.close()

    return data, count


@API_ROUTER.get("/get_trades", response_class=JSONResponse, response_model=RichListGetDenoms)
async def get_trades(swth_taker_address: str = Query(None, length=43, description="TradeHub 'swth1' taker wallet."),
                     swth_maker_address: str = Query(None, length=43, description="TradeHub 'swth1' maker wallet."),
                     before_id: int = Query(None, description="Only show trades before(exclusive) provided ID."),
                     after_id: int = Query(None, description="Only show trades after(exclusive) provided ID."),
                     before: str = Query(None, description="Only show trades before(exclusive) ISO8601 timestamp."),
                     after: str = Query(None, description="Only show trades after(exclusive) ISO8601 timestamp."),
                     market: str = Query(None, min_length=3, max_length=6, description="Limit the result to a specific market"),
                     offset: int = Query(0, ge=0, description="Request result with offset."),
                     limit: int = Query(100, ge=1, le=100, description="Limit the response result."),):
    """
    Request currently managed coins. To all returned coins there is a richlist available.
    """
    data, count = db_get_trades(swth_taker_address, swth_maker_address, before_id, after_id, before, after, market)
    if count > SQL_LIMIT:
        return JSONResponse({
            "error": f"Requested dataset is to big with {count} entries. The server only processes a limit of {SQL_LIMIT} entries. Specify your request!"
        }, status_code=413)
    if limit:
        data = data[offset:offset+limit]
    trades = [

    ]
    for trade in data:
        trades.append({
            "id": trade[0],
            "timestamp": trade[1].isoformat(),
            "block": trade[10],
            "taker": trade[2],
            "maker": trade[3],
            "is_buy": trade[4],
            "market": trade[7].replace(" ", ""),
            "price": str(trade[8]),
            "quantity": str(trade[9]),
            "volume": str(trade[11]),
            "taker_fee": str(trade[5]),
            "taker_fee_usd": str(trade[12]),
            "maker_fee": str(trade[6]),
            "maker_fee_usd": str(trade[13]),
        })

    return JSONResponse({
        "total": count,
        "offset": offset,
        "limit": limit,
        "trades": trades
    }, status_code=200)


@API_ROUTER.get("/24h/get_trades", response_class=JSONResponse, response_model=RichListGetDenoms)
async def get_24h_trades(swth_taker_address: str = Query(None, length=43, description="TradeHub 'swth1' taker wallet."),
                         swth_maker_address: str = Query(None, length=43, description="TradeHub 'swth1' maker wallet."),
                         before_id: int = Query(None, description="Only show trades before(exclusive) provided ID."),
                         after_id: int = Query(None, description="Only show trades after(exclusive) provided ID."),
                         market: str = Query(None, min_length=3, max_length=6, description="Limit the result to a specific market"),
                         offset: int = Query(0, ge=0, description="Request result with offset."),
                         limit: int = Query(100, ge=1, le=100, description="Limit the response result.")):
    current_time: datetime = datetime.now()
    after: datetime = current_time - timedelta(days=1)
    return await get_trades(swth_taker_address, swth_maker_address,
                            before_id, after_id,
                            None,
                            after.isoformat(),
                            market,
                            offset,
                            limit)


def db_get_dominance(market: Optional[str], before: Optional[str], after: Optional[str]):
    global DATABASE_CONFIG, SQL_LIMIT

    where_clauses = []

    if before:
        where_clauses.append(f"time< timestamp '{before}'")

    if after:
        where_clauses.append(f"time > timestamp '{after}'")

    if market:
        where_clauses.append(f"market='{market}'")

    where: str = ""
    if where_clauses:
        where: str = f"WHERE " + " AND ".join(where_clauses)

    sql_total = f"SELECT SUM(volume) FROM public.trades {where}"
    sql_query = f"SELECT taker, SUM(volume) FROM public.trades {where} GROUP BY taker ORDER BY 2 DESC LIMIT 100"

    with connect(DATABASE_CONFIG) as conn:
        cur = conn.cursor()

        cur.execute(sql_total)

        total = cur.fetchone()[0]

        cur.execute(sql_query)

        data = cur.fetchall()

        cur.close()

    return total, data


@API_ROUTER.get("/get_dominance", response_class=JSONResponse, response_model=RichListGetDenoms)
async def get_dominance(market: str = Query(None, min_length=3, max_length=15, description="Limit the result to a specific market"),
                        before: str = Query(None, description="Only show trades before(exclusive) ISO8601 timestamp."),
                        after: str = Query(None, description="Only show trades after(exclusive) ISO8601 timestamp."),):
    total, data = db_get_dominance(market, before, after)
    print(total)

    takers = [

    ]
    for taker in data:
        print(taker)
        takers.append({
            "taker": taker[0],
            "volume": str(taker[1]),
            "dominance": f"{taker[1]/total * 100:.4f}"
        })

    return JSONResponse({
        "total": str(total),
        "takers": takers
    }, status_code=200)


@API_ROUTER.get("/24h/get_dominance", response_class=JSONResponse, response_model=RichListGetDenoms)
async def get_24h_dominance(market: str = Query(None, min_length=3, max_length=15, description="Limit the result to a specific market")):
    current_time: datetime = datetime.now()
    after: datetime = current_time - timedelta(days=1)
    return await get_dominance(market, None, after.isoformat())


def db_get_market_volume(before, after):
    global DATABASE_CONFIG, SQL_LIMIT

    where_clauses = []

    if before:
        where_clauses.append(f"time< timestamp '{before}'")

    if after:
        where_clauses.append(f"time > timestamp '{after}'")

    where: str = ""
    if where_clauses:
        where: str = f"WHERE " + " AND ".join(where_clauses)

    sql_total = f"SELECT SUM(volume) FROM public.trades {where}"
    sql_query = f"SELECT market, SUM(volume) FROM public.trades {where} GROUP BY market ORDER BY 2 DESC"

    with connect(DATABASE_CONFIG) as conn:
        cur = conn.cursor()

        cur.execute(sql_total)

        total = cur.fetchone()[0]

        cur.execute(sql_query)

        data = cur.fetchall()

        cur.close()

    return total, data


@API_ROUTER.get("/market/get_volume", response_class=JSONResponse, response_model=RichListGetDenoms)
async def get_market_volume(before: str = Query(None, description="Only show trades before(exclusive) ISO8601 timestamp."),
                        after: str = Query(None, description="Only show trades after(exclusive) ISO8601 timestamp.")):
    total, data = db_get_market_volume(before, after)
    print(total)

    markets = [

    ]
    for market in data:
        markets.append({
            "market": market[0].replace(" ", ""),
            "volume": str(market[1]),
            "dominance": f"{market[1]/total * 100:.4f}"
        })

    return JSONResponse({
        "total": str(total),
        "markets": markets
    }, status_code=200)


@API_ROUTER.get("/24h/market/get_volume", response_class=JSONResponse, response_model=RichListGetDenoms)
async def get_24h_market_volume():
    current_time: datetime = datetime.now()
    after: datetime = current_time - timedelta(days=1)
    return await get_market_volume( None, after.isoformat())