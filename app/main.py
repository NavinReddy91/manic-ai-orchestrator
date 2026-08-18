"""
Manic AI Orchestrator — FastAPI Application
"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}"
    )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


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
    allow_credentials=origins != ["*"],  # credentials not allowed with wildcard
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
    logger.info(f"Checking frontend path: {path} (exists={path.exists()})")
    if path.exists() and (path / "index.html").exists():
        FRONTEND_DIR = path
        logger.info(f"✓ Frontend directory found at: {FRONTEND_DIR}")
        break

if not FRONTEND_DIR:
    logger.warning(
        "✗ Frontend directory not found in any location. Serving API-only mode."
    )
    logger.warning(f"Current working directory: {Path.cwd()}")
    logger.warning(f"__file__ location: {Path(__file__)}")

if FRONTEND_DIR:
    # Mount static files first (CSS, JS)
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    def root():
        """Serve the frontend UI."""
        index_path = FRONTEND_DIR / "index.html"
        return FileResponse(index_path, media_type="text/html")
else:
    logger.warning("Frontend directory not found. Serving embedded fallback UI.")

    @app.get("/", response_class=HTMLResponse)
    def root():
        """Serve embedded fallback UI."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Manic AI - Deployment Issue</title>
            <style>
                body { font-family: monospace; background: #0a0e1a; color: #00f0ff; padding: 2rem; }
                .container { max-width: 800px; margin: 0 auto; }
                h1 { color: #00f0ff; text-shadow: 0 0 10px rgba(0,240,255,0.5); }
                .error { color: #ff3366; }
                .info { background: rgba(0,240,255,0.1); padding: 1rem; border-left: 3px solid #00f0ff; margin: 1rem 0; }
                code { background: rgba(0,0,0,0.3); padding: 0.2rem 0.5rem; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠ Frontend Not Found</h1>
                <p class="error">The frontend directory was not found during deployment.</p>
                <div class="info">
                    <strong>API Status:</strong> ✓ Running<br>
                    <strong>Frontend:</strong> ✗ Not Found
                </div>
                <h2>Quick Links</h2>
                <ul>
                    <li><a href="/docs" style="color:#00f0ff">API Documentation (/docs)</a></li>
                    <li><a href="/health" style="color:#00f0ff">Health Check (/health)</a></li>
                </ul>
                <h2>Troubleshooting</h2>
                <p>Check Render logs for path resolution details. The app checked these locations:</p>
                <ul>
                    <li><code>Path(__file__).parent.parent / "frontend"</code></li>
                    <li><code>Path.cwd() / "frontend"</code></li>
                    <li><code>Path("/app/frontend")</code></li>
                </ul>
                <p>Ensure the <code>frontend/</code> directory is in your repository and deployed correctly.</p>
            </div>
        </body>
        </html>
        """


@app.get("/health")
def health():
    return {"status": "ok", "service": "manic-ai-orchestrator", "version": "1.0.0"}


@app.get("/debug/llm-test")
async def llm_test():
    """Test endpoint to verify LLM connection is working."""
    from .llm import call_llm
    from .config import settings

    if not settings.llm_api_key:
        return {
            "error": "LLM_API_KEY not configured",
            "provider": settings.llm_provider,
        }

    try:
        response = await call_llm(
            "You are a test assistant.",
            "Say 'LLM connection successful' in exactly those words.",
            max_tokens=50,
        )
        return {
            "status": "success",
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "response": response,
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "error": str(e),
        }
