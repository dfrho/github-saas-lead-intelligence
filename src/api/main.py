"""
FastAPI application entry point.

Run locally:
    uvicorn src.api.main:app --reload --port 8000

The MCP server (server.py) continues to work independently — this file
adds a web API layer on top of the same src/services/ functions.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .routers import repos, reports, users
from scheduler.worker import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate required env vars are present
    required = ["DATABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="GitHub Lead Intelligence API",
    description="Convert GitHub engineering activity into structured B2B sales leads.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend origin (configure via env in production)
_frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router)
app.include_router(reports.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok"}
