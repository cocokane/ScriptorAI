"""Main FastAPI application for Scriptor Local."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .api import router, startup, shutdown
from .config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting Scriptor Local on port {config.server_port}")
    logger.info(f"Storage directory: {config.storage_dir}")
    await startup()
    yield
    await shutdown()
    logger.info("Scriptor Local shut down")


app = FastAPI(
    title="Scriptor Local",
    description="Local companion API for ScriptorAI Chrome Extension",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - only allow localhost/extension origins
# The extension will use the auth token for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "http://localhost:*",
        "http://127.0.0.1:*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Scriptor Local",
        "version": "1.0.0",
        "status": "running",
        "api_docs": "/docs"
    }


def run_server():
    """Run the server using uvicorn."""
    import uvicorn
    uvicorn.run(
        "scriptor_local.app:app",
        host="127.0.0.1",
        port=config.server_port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
