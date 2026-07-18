"""Small JSON HTTP transport shared by SiYuan and remote MCP clients."""

from __future__ import annotations

import json
from urllib.request import Request, urlopen


class JsonTransport:
    def post(self, url: str, payload: dict, token: str = "", timeout: float = 15) -> dict:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Token {token}"
        request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URLs are explicit local config
            return json.loads(response.read().decode())
