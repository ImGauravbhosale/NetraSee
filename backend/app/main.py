from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit_log, auth, controls, dashboard, evidence, frameworks, members
from app.api.deps import require_csrf

app = FastAPI(title="NetraSee API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSRF is checked once here for every mutating request across the whole
# API, rather than repeated per-router — the state-changing routers don't
# need to remember to add it themselves.
app.include_router(auth.router)
app.include_router(frameworks.router, dependencies=[Depends(require_csrf)])
app.include_router(controls.router, dependencies=[Depends(require_csrf)])
app.include_router(evidence.router, dependencies=[Depends(require_csrf)])
app.include_router(dashboard.router)
app.include_router(audit_log.router)
app.include_router(members.router, dependencies=[Depends(require_csrf)])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}
