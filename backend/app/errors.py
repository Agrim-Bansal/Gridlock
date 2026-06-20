from fastapi import Request
from fastapi.responses import JSONResponse


class GridlockError(Exception):
    def __init__(self, status_code: int, error: str, message: str):
        self.status_code = status_code
        self.error = error
        self.message = message


async def gridlock_error_handler(
    request: Request, exc: GridlockError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message},
    )
