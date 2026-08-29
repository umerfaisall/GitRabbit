from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, prs, webhook

app = FastAPI(title="PR Review Orchestrator (mock)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(prs.router)
app.include_router(webhook.router)