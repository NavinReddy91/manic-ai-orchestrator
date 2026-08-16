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


app = FastAPI(title="Manic AI Orchestrator", version="0.4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://digimarkin.com", "https://nexus.digimarkin.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(github_router)
app.include_router(tasks_router)
app.include_router(organizations_router)
app.include_router(admin_router)
app.include_router(templates_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "manic-ai-orchestrator"}
