# Security Policy

Concord Voice builds privacy- and security-critical software. We take vulnerabilities seriously and genuinely appreciate responsible disclosure.

## Reporting a vulnerability

**Please do not open public issues, pull requests, or discussions for security vulnerabilities.**

Report privately to **[security@concordvoice.com](mailto:security@concordvoice.com)**. A PGP key is available on request.

Where possible, please include:

- A description of the issue and its potential impact
- Steps to reproduce, or a proof-of-concept
- Affected component(s) and version(s)
- Any suggested remediation

## What to expect

| Stage | Target |
| :-- | :-- |
| Acknowledgement of your report | within **3 business days** |
| Triage and severity assessment (CVSS) | within **7 business days** |
| Coordinated fix & disclosure | we'll keep you updated throughout |

We will credit you for the discovery once a fix ships, unless you prefer to remain anonymous. Please give us a reasonable window to remediate before any public disclosure.

## Scope

This policy applies to all repositories under the [Concord Voice organization](https://github.com/Concord-Voice) and the services hosted at `concordvoice.com` and `concordvoice.chat`.

## Our security posture

Concord Voice is engineered for defense in depth:

- **End-to-end encryption:** AES-256-GCM with RSA-OAEP 4096-bit key wrapping and epoch-based key rotation
- **Credential protection:** Argon2id password hashing; OS-keychain-backed storage on desktop
- **Strong authentication:** multi-factor auth (TOTP + WebAuthn/passkeys)
- **Access control:** role-based and scope-based permissions

Thank you for helping keep Concord Voice and its users safe.
