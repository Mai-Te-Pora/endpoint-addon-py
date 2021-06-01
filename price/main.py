from threading import Thread
import uvicorn
from fastapi import FastAPI
from endpoint import API_ROUTER
from price import load_predefined_coins, main_current_price, main_history_data

if __name__ == "__main__":
    load_predefined_coins()
    main_price_current_thread = Thread(target=main_current_price)
    main_price_current_thread.setName("Price current price")
    main_price_current_thread.start()
    main_price_historic_thread = Thread(target=main_history_data)
    main_price_historic_thread.setName("Price historic price")
    main_price_historic_thread.start()
    app = FastAPI()
    app.include_router(API_ROUTER, prefix="/price", tags=["Price"])
    uvicorn.run(app, host="0.0.0.0", port=8002, loop="asyncio")
