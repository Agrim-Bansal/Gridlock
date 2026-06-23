import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class GridlockError(Exception):
    def __init__(self, status_code: int, error: str, message: str):
        self.status_code = status_code
        self.error = error
        self.message = message


async def gridlock_error_handler(
    request: Request, exc: GridlockError
) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error(
            "%s %s → %d %s: %s",
            request.method, request.url.path, exc.status_code, exc.error, exc.message,
        )
    else:
        logger.info(
            "%s %s → %d %s: %s",
            request.method, request.url.path, exc.status_code, exc.error, exc.message,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message},
    )
