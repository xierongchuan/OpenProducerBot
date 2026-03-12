import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .routes import dashboard, trades, charts, logs, config_routes, journal, chart_data
from .services.file_watcher import FileWatcher
from .ws import manager

logger = logging.getLogger("panel.app")

file_watcher: FileWatcher | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global file_watcher

    # Log config paths for diagnostics
    from .config import DATA_DIR, CHARTS_DIR, CONFIG_PATH, PROJECT_ROOT
    logger.info("Config paths:")
    logger.info("  PROJECT_ROOT: %s (exists=%s)", PROJECT_ROOT, PROJECT_ROOT.is_dir())
    logger.info("  CONFIG_PATH: %s (exists=%s)", CONFIG_PATH, CONFIG_PATH.exists())
    logger.info("  DATA_DIR: %s (exists=%s)", DATA_DIR, DATA_DIR.is_dir())
    logger.info("  CHARTS_DIR: %s (exists=%s)", CHARTS_DIR, CHARTS_DIR.is_dir())

    # Check new config system
    config_dir = CONFIG_PATH.parent / "config"
    logger.info("  CONFIG_DIR: %s (exists=%s)", config_dir, config_dir.is_dir())
    if config_dir.is_dir():
        logger.info("  active.json exists: %s", (config_dir / "active.json").exists())

    loop = asyncio.get_running_loop()
    file_watcher = FileWatcher(loop=loop)
    file_watcher.set_ws_manager(manager)
    file_watcher.start()
    logger.info("Panel backend started")
    yield
    file_watcher.stop()
    logger.info("Panel backend stopped")


app = FastAPI(title="OpenProducerBot Panel", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions, log them, and return detailed error for debugging."""
    tb = traceback.format_exc()
    logger.error("Unhandled exception on %s %s: %s\n%s", request.method, request.url.path, exc, tb)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "path": request.url.path,
        },
    )


# CORS for Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://web.telegram.org", "https://telegram.org", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(dashboard.router)
app.include_router(trades.router)
app.include_router(charts.router)
app.include_router(logs.router)
app.include_router(config_routes.router)
app.include_router(journal.router)
app.include_router(chart_data.router)


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; handle incoming messages if needed
            data = await websocket.receive_text()
            # Client messages (e.g. subscribe) can be handled here in the future
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# Mount static frontend build (must be last so API routes take priority)
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
