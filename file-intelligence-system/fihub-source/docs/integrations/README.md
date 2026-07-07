# Integration Library

The integration library is the catalog of outside systems the hub can talk to.

It should answer:

- What is this system?
- Where is its API?
- What can it do?
- Does it need a token or local bridge?
- Is it safe to run directly, or should actions go through review?

## Examples

- NAS devices and shared folders
- Syncthing
- Cloudflare R2
- GitHub
- local OCR tools
- AutoHotkey bridges
- command-line AI tools
- desktop apps controlled by a local bridge
- Postgres or SQLite databases
- vector databases and embedding services

## Registry

Start with:

`config/integrations/integrations.example.json`

Each integration gets:

- `integration_id`: stable machine name
- `label`: human name
- `kind`: storage, sync, ai, desktop_bridge, database, object_storage, etc.
- `status`: active, planned, disabled, broken
- `base_url`: API URL when one exists
- `capabilities`: what the hub can ask it to do
- `auth`: how secrets are referenced
- `metadata`: notes and special handling

## How It Fits

The hub should not hard-code every outside program. It should look up a capability in the integration library, then hand the work to the right connector.

For example:

1. A file lands in a watched folder.
2. The hub tags it and decides it belongs in long-term storage.
3. The hub checks the integration library for a storage target.
4. It creates a reviewed file action or connector job.
5. The result is written to the ledger.

That keeps NAS, R2, Syncthing, OCR, AHK, and future tools from becoming a pile of one-off scripts.
