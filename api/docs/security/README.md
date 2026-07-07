# Security and Secrets

The hub should not store raw passwords in SQLite, JSON config, git, logs, or message history.

## Rule

Store a reference, not the secret.

Examples:

- `NAS_API_TOKEN`
- `SYNCTHING_API_KEY`
- `CLOUDFLARE_API_TOKEN`
- `OPENAI_API_KEY`

The integration registry can say `secret_ref`, but the actual value should live in one of:

- Windows Credential Manager
- environment variables
- a local `.env` file that is never committed
- a future dedicated vault service

## Why

The hub will eventually route messages, file actions, command-line jobs, memory, and integrations. That means logs and database rows will be inspected often. Secrets should not be mixed into normal operational data.

## API Pattern

Good:

```json
{
  "integration_id": "nas-primary",
  "auth": {
    "type": "manual",
    "secret_ref": "NAS_API_TOKEN"
  }
}
```

Bad:

```json
{
  "password": "actual-password-here"
}
```

## Command Safety

Command-line jobs should default to review-required. The hub records the command, result, stdout, stderr, and return code in the job ledger so a human can inspect what happened.

## Login Passwords

For user login, SQLite may store password hashes, not passwords.

See `sqlite-access-control.md` for the password-protected history model.

Acceptable:

- user id
- username
- password hash from a strong password hasher
- password salt/hash parameters
- MFA enabled flag
- per-user history visibility settings

Not acceptable:

- plaintext password
- reusable API tokens
- Synology/NAS password
- OpenAI/API provider key
- MFA recovery codes in plain text

## Separate Histories

The hub should support per-user ownership on sensitive records.

Examples:

- David can see David's private history.
- Codex can see Codex/system history.
- Shared project history is visible to allowed users/agents.

This should be enforced by API authorization later, not by hiding rows in the frontend.

## MFA

MFA can be added later, but MFA seed secrets must be encrypted or stored through a secret manager. SQLite can store the fact that MFA is enabled and a `secret_ref`; it should not casually store raw MFA seeds.
