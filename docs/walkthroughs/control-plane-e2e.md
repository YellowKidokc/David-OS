# End-to-end control-plane walkthrough

1. Start the FastAPI hub with `uvicorn file_intelligence_hub.api.app:app --host 127.0.0.1 --port 10000` from the `api` package context.
2. Start the Desk app with `npm run dev` from `apps/desk`.
3. Open Desk, confirm the live indicator points at `http://127.0.0.1:10000`, and use `Ctrl/Cmd+K` to open the universal command palette.
4. Choose **Open clipboard workspace**.
5. Save clipboard records through `/clipboard/save` or the AHK bridge, then filter by app, window, folder, tag, type, date, pinned, and deleted state.
6. Select records, merge them into the composer, export as Markdown/text/JSON, or copy an item through `/clipboard/items/{id}/copy` for AHK/browser clipboard handoff.
7. Use destructive actions only through the existing review-gated operator routes.
