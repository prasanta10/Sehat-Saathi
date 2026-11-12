"""Structured JSON logs with request IDs. Logs carry IDs, routes, statuses, timings and versions —
never transcripts, names or fact values (tested by the sentinel scan)."""

from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_SAFE_EXTRA = ("provider", "attempt", "status", "route", "method", "ms", "reason")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id.get(),
        }
        for k in _SAFE_EXTRA:
            if hasattr(record, k):
                out[k] = getattr(record, k)
        return json.dumps(out, ensure_ascii=False)


def configure() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("sehat")
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    root.propagate = False


async def request_logging(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    token = request_id.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")  # the template, e.g. /encounters/{encounter_id}
        logging.getLogger("sehat.http").info(
            "request",
            extra={
                "method": request.method,
                "route": path,
                "status": response.status_code,
                "ms": round((time.perf_counter() - start) * 1000),
            },
        )
    finally:
        request_id.reset(token)
    response.headers["x-request-id"] = rid
    return response
