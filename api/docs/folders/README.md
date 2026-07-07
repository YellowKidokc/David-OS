# Folder API

Every folder created by the frontend, AHK, or another agent should be created through the API.

API:

- `POST /folders`
- `GET /folders`
- `GET /folders/{folder_id}`
- `PATCH /folders/{folder_id}/archive`

Folders support:

- stable `folder_code`
- generated custom codes starting at `60020`
- nested parent/child folders
- wall assignment
- owner id
- visibility
- metadata
- archive state

Example:

```json
{
  "name": "API Calls",
  "wall": "code",
  "wall_code": 50006,
  "owner_id": "david",
  "visibility": "shared"
}
```

The API returns:

```json
{
  "folder_code": 60020,
  "name": "API Calls",
  "slug": "api-calls"
}
```

Rule: the frontend should not invent durable folder IDs locally. It can create temporary UI placeholders, but it should sync them through `POST /folders` immediately.
