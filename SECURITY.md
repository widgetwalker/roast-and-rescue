# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Security Architecture & Defenses

GitHub Roast & Rescue enforces defensive security standards across all layers:

1. **Zero Secret Storage**: Never requests, stores, or logs OAuth access tokens, passwords, or personal access tokens.
2. **Defensive Rate Limiting**: In-memory IP window limiting (120 req/minute) shields public endpoints from DoS spikes.
3. **HTTP Security Headers**: Enforces `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`, and strict Referrer policies.
4. **Input Sanitization & Injection Defense**: GitHub usernames are strictly validated against `/^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/` to prevent directory traversal and injection attacks.
5. **Payload Size Caps**: Body parsing capped at 20MB with character constraints on user uploads.

## Reporting a Vulnerability

If you discover a security vulnerability within this repository, please report it privately:

- **Email**: `dheeraj5765483@gmail.com`
- **Response SLA**: Initial triage within 24 hours; remediation patch within 72 hours.
- Please do not disclose vulnerabilities publicly via GitHub Issues prior to patch deployment.
