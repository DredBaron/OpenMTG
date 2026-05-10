# Security Policy

## Supported Versions

Only the latest release on the `main` branch receives security fixes. The `dev` branch is unstable and not supported for production use.

| Branch | Supported |
|--------|-----------|
| `main` (latest release) | Yes |
| `dev` | No |
| Older releases | No |

---

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Use [GitHub's private vulnerability reporting](https://github.com/DredBaron/OpenMTG/security/advisories/new) to submit a report confidentially. Include as much detail as you can:

- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- The version or commit you tested against
- Any suggested mitigations, if you have them

This project is maintained by one person. You can expect an acknowledgement within a couple days and a fix or update within a reasonable timeframe depending on severity.

---

## Scope

OpenMTG is a self-hosted application. The following are in scope:

- Authentication and session handling (JWT, login, token expiry)
- Authorization bypass (accessing or modifying another user's collection, decks, or wishlist)
- Admin privilege escalation by a non-admin user
- SQL injection or data exposure via API endpoints
- Sensitive data leakage (e.g. hashed passwords returned in responses)

The following are **out of scope**:

- Vulnerabilities that require physical access to the host machine
- Issues in the host OS, Docker daemon, or PostgreSQL itself
- Denial-of-service attacks against a self-hosted instance you do not own
- Security of third-party dependencies beyond what affects OpenMTG directly (report those upstream)
- Issues only reproducible with a misconfigured deployment (e.g. a weak `JWT_SECRET` chosen by the operator)

---

## Security Design Notes

These are the current security properties of the application. They are documented here to help researchers understand the intended design.

- **Authentication** - JWT tokens signed with HMAC-SHA256. Tokens expire after 7 days.
- **Passwords** - Hashed with bcrypt. Plaintext passwords are never stored or logged.
- **Authorization** - Every data endpoint checks the authenticated user's identity. Users can only read or modify their own collections, decks, and wishlists. Admin-only endpoints are gated separately.
- **Rate limiting** - API rate limiting is applied via slowapi. Scryfall API calls are limited to 2 requests per second, no exceptions.
- **Telemetry** - Opt-in only. Sends only an anonymous random ID and a timestamp. No personal data is transmitted.

---

## Operator Responsibilities

OpenMTG is self-hosted software. The security of your deployment depends on choices you make as the operator:

- Use a strong, randomly generated `JWT_SECRET` (at least 32 bytes - `openssl rand -hex 32` works well).
- Do not expose the PostgreSQL port publicly.
- Run behind HTTPS in production. The included Nginx configuration handles this.
- Keep your Docker image up to date by pulling new releases when they are published.
