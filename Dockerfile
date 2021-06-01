FROM python:3.7-alpine3.11

RUN apk update
RUN apk add bash gcc linux-headers musl-dev g++ postgresql-dev

RUN pip install aiofiles==0.6.0 fastapi==0.61.1 pydantic==1.7.2 requests==2.24.0 starlette==0.13.6 uvicorn==0.12.2 eventlet==0.29.1 httpx==0.16.1 aiohttp iso8601 psycopg2-binary

COPY . /home/endpoint

WORKDIR /home/endpoint/

RUN pip install .