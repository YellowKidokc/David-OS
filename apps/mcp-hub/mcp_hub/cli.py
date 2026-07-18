"""Command-line entry points."""

from .config import Settings


def http_main() -> None:
    import uvicorn

    settings = Settings()
    uvicorn.run("mcp_hub.app:app", host=settings.host, port=settings.port)
