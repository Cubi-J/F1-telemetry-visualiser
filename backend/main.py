from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from historic import router as historic_router
from live import router as live_router, live_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start live/replay broadcast engine
    await live_engine.start()
    yield
    # Shutdown: Clean up background loops and connections
    await live_engine.stop()


app = FastAPI(
    title="F1 Telemetry Visualizer API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(historic_router)
app.include_router(live_router)
