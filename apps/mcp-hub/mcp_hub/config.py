"""Environment-backed MCP Hub settings with conservative local defaults."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    siyuan_host: str = field(default_factory=lambda: os.getenv("SIYUAN_HOST", "127.0.0.1"))
    siyuan_port: int = field(default_factory=lambda: int(os.getenv("SIYUAN_PORT", "6806")))
    siyuan_token: str = field(default_factory=lambda: os.getenv("SIYUAN_TOKEN", ""))
    host: str = field(default_factory=lambda: os.getenv("MCP_HUB_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("MCP_HUB_PORT", "8787")))
    allow_writes: bool = field(default_factory=lambda: _flag("ALLOW_WRITES"))
    max_context_chars: int = field(default_factory=lambda: int(os.getenv("MAX_CONTEXT_CHARS", "6000")))
    max_response_chars: int = field(default_factory=lambda: int(os.getenv("MAX_RESPONSE_CHARS", "20000")))
    debug_content: bool = field(default_factory=lambda: _flag("DEBUG_CONTENT"))
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(item.strip() for item in os.getenv("MCP_HUB_CORS_ORIGINS", "*").split(",") if item.strip()))
    remote_servers: tuple[dict, ...] = field(default_factory=lambda: tuple(json.loads(os.getenv("MCP_SERVERS_JSON", "[]"))))

    @property
    def siyuan_url(self) -> str:
        return f"http://{self.siyuan_host}:{self.siyuan_port}"
