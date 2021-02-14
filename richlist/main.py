import uvicorn
from threading import Thread
from fastapi import FastAPI
import richlist.endpoint
from richlist import update_richlist, update_block_height


if __name__ == "__main__":
    main_richlist_thread = Thread(target=update_richlist)
    main_richlist_thread.setName("RichList Update Thread")
    main_richlist_thread.start()
    update_block_height_thread = Thread(target=update_block_height)
    update_block_height_thread.setName("RichList Block Height Thread")
    update_block_height_thread.start()
    tags_metadata = [
        {
            "name": "RichList",
            "description": "Tracks all staking wallets and sort them by their total balance per coin.",
            "version": "0.1.0"
        }
    ]
    app = FastAPI(title="Additional Tradehub Python API Endpoints",
                  description="The default API endpoints are lacking of some few interesting data or do not allow simple requests. These endpoints are designed to provide simple to use data.",
                  version="0.1.0",
                  openapi_tags=tags_metadata)
    app.include_router(richlist.endpoint.API_ROUTER, prefix="/richlist", tags=["RichList"])
    uvicorn.run(app, host="0.0.0.0", port=8001, loop="asyncio")
