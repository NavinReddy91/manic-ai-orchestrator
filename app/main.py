"""
Manic AI Orchestrator — FastAPI Application
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from .db import init_db
from .github_oauth import router as github_router
from .tasks_api import router as tasks_router
from .organizations_api import router as organizations_router
from .admin_api import router as admin_router
from .task_templates_api import router as templates_router
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    yield


app = FastAPI(
    title="Manic AI Orchestrator",
    version="1.0.0",
    description="Multi-agent AI orchestration engine with hierarchical task delegation",
    lifespan=lifespan,
)

# CORS configuration
from .config import settings

origins = (
    [o.strip() for o in settings.allowed_origins.split(",")]
    if settings.allowed_origins != "*"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(github_router)
app.include_router(tasks_router)
app.include_router(organizations_router)
app.include_router(admin_router)
app.include_router(templates_router)

# Serve static frontend files
# Try multiple possible locations for the frontend directory
POSSIBLE_FRONTEND_DIRS = [
    Path(__file__).parent.parent / "frontend",  # Standard layout
    Path.cwd() / "frontend",  # Current working directory
    Path("/app/frontend"),  # Render deployment
    Path("./frontend"),  # Relative path
]

FRONTEND_DIR = None
for path in POSSIBLE_FRONTEND_DIRS:
    if path.exists() and (path / "index.html").exists():
        FRONTEND_DIR = path
        logger.info(f"Frontend directory found at: {FRONTEND_DIR}")
        break

if FRONTEND_DIR:
    # Mount static files first (CSS, JS)
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    def root():
        """Serve the frontend UI."""
        index_path = FRONTEND_DIR / "index.html"
        return FileResponse(index_path, media_type="text/html")
else:
    logger.warning("Frontend directory not found. Serving API-only mode.")

    @app.get("/")
    def root():
        return {
            "name": "Manic AI Orchestrator",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "message": "Frontend not found. API is running. Visit /docs for API documentation.",
        }


@app.get("/health")
def health():
    return {"status": "ok", "service": "manic-ai-orchestrator", "version": "1.0.0"}
