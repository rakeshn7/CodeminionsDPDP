from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.audit.logger import AuditStore
from app.config import Settings
from app.services.gateway import Gateway


def create_app(
    settings: Settings | None = None, gateway: Gateway | None = None
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    audit_store = gateway.audit if gateway else AuditStore(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        audit_store.initialize()
        app.state.settings = resolved_settings
        app.state.gateway = gateway or Gateway(resolved_settings, audit_store)
        yield

    application = FastAPI(
        title="DPDP Privacy Gateway",
        description=(
            "Detects and masks personal data locally, verifies sanitized outbound "
            "requests, and restores known placeholders locally."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.gateway = gateway or Gateway(resolved_settings, audit_store)
    audit_store.initialize()
    application.include_router(router)
    return application


app = create_app()
