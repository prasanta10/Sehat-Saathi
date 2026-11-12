"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__, logging_setup
from app.api import admin, auth, content, encounters, health, persons, schemes
from app.config import get_settings
from app.services.errors import DomainError

PROBLEM = "application/problem+json"


def create_app() -> FastAPI:
    settings = get_settings()
    logging_setup.configure()
    app = FastAPI(title="Sehat Saathi API", version=__version__)
    app.middleware("http")(logging_setup.request_logging)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        body = {
            "type": "about:blank",
            "title": exc.code,
            "status": exc.status,
            "code": exc.code,
            "detail": exc.detail,
        }
        return JSONResponse(body, status_code=exc.status, media_type=PROBLEM)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Field locations only; never echo submitted values (they may contain patient text).
        errors = [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
        body = {
            "type": "about:blank",
            "title": "validation_error",
            "status": 422,
            "code": "validation_error",
            "errors": errors,
        }
        return JSONResponse(body, status_code=422, media_type=PROBLEM)

    # Health endpoints are served both at the root (for infrastructure) and under the API prefix.
    app.include_router(health.router)
    for r in (
        health.router,
        auth.router,
        persons.router,
        encounters.router,
        content.router,
        admin.router,
        schemes.router,
    ):
        app.include_router(r, prefix="/api/v1")
    return app


app = create_app()
