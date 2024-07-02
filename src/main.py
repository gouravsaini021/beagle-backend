from fastapi import FastAPI
from typing import List
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from typing import AsyncGenerator

from .db import engine,Base
from src.api import softupload,heartbeat,print2wa


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Connect to the database
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Close the database connection
    await engine.dispose()


sentry_sdk.init(
    dsn="https://55c726ce37e4f6fa23de011c546731ad@o4507208886386688.ingest.us.sentry.io/4507208890253312",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    enable_tracing=True,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

    

app=FastAPI(lifespan=lifespan,docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],  # Adjust this to the specific origins you want to allow
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)


app.include_router(softupload.router)
app.include_router(heartbeat.router)
app.include_router(print2wa.router)