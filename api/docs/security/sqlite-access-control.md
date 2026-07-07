# SQLite Access Control

SQLite can be the storage engine for private histories, but SQLite itself should not be treated like the login system.

The hub API should be the gate.

## What Goes In SQLite

Acceptable:

- user account id
- display name
- role, such as `owner`, `agent`, `viewer`
- password hash from a strong password hasher
- MFA enabled flag
- MFA `secret_ref`
- session records or revoked session ids
- ownership fields on messages, memory, files, and history rows
- visibility, such as `private`, `shared`, or `system`

Not acceptable:

- plaintext passwords
- raw MFA seed secrets
- API keys
- NAS passwords
- reusable provider tokens

## How The Lock Works

The API receives a login request, checks the submitted password against the stored password hash, then issues a session or token.

After that:

- David can read rows owned by `david` plus shared rows.
- Codex/system can read system rows plus allowed shared rows.
- Another agent can only read rows assigned to that agent or shared with it.
- Admin/owner can grant or revoke access.

The frontend should not be trusted to hide private rows. The API must enforce it before data leaves SQLite.

## MFA

MFA is a second gate after the password.

SQLite can store:

- `mfa_enabled = true`
- `mfa_secret_ref = "DAVID_MFA_SECRET"`

The actual MFA seed should be encrypted or kept in a secret manager. If we temporarily store it locally during development, it should be treated as sensitive and never committed.

## Future Table Shape

Likely tables:

- `users`
- `sessions`
- `access_grants`
- `audit_logins`

Likely owner columns on data tables:

- `owner_id`
- `visibility`
- `shared_with_json`

This gives us the password-protected history you mean, without putting readable passwords inside the database.
