# AutoHotkey Controllers

This folder holds AutoHotkey scripts that act as the local "hands" for Top of Mind.

Current purpose:

- control AI/chat windows
- type messages from the API into target apps
- click send/start/stop buttons
- capture clipboard or window text
- post results back to the hub

Current files:

- `ai_chat_controller.ahk`: general AI chat controller.
- `claude_chat_controller.ahk`: Claude-specific controller.
- `AI Chat Controller - Complete Operations Guide.md`: operating guide.

Default hub URL should follow the numbering schema:

```text
http://127.0.0.1:10000
```

On another computer, use the hub machine IP:

```text
http://192.168.2.50:10000
```

AutoHotkey should stay the hands. Routing, memory, security, and file decisions should stay in `apps/api`.
