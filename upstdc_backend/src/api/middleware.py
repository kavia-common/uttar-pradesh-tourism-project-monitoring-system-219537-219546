from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from typing import Callable
from src.api.db.mongo import get_db


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to record audit logs for each request."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        try:
            db = get_db()
            user_id = request.headers.get("x-user-id")  # fallback if JWT not parsed
            path = request.url.path
            method = request.method
            ip = request.client.host if request.client else None

            await db.audit_logs.insert_one(
                {
                    "user_id": user_id,
                    "path": path,
                    "method": method,
                    "status_code": response.status_code,
                    "ip": ip,
                    "timestamp": datetime.utcnow(),
                }
            )
        except Exception:
            # best effort audit
            pass

        return response
