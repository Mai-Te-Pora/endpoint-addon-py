import uvicorn
from fastapi import FastAPI
from endpoint import API_ROUTER


if __name__ == "__main__":
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
    app.include_router(API_ROUTER, prefix="/trading", tags=["Trading"])
    uvicorn.run(app, host="0.0.0.0", port=8003, loop="asyncio")