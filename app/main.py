"""
Manic AI Orchestrator — FastAPI Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .github_oauth import router as github_router
from .tasks_api import router as tasks_router
from .organizations_api import router as organizations_router
from .admin_api import router as admin_router
from .task_templates_api import router as templates_router
from .logging_config import setup_logging


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


@app.get("/health")
def health():
    return {"status": "ok", "service": "manic-ai-orchestrator", "version": "1.0.0"}


@app.get("/")
def root():
    return {
        "name": "Manic AI Orchestrator",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
