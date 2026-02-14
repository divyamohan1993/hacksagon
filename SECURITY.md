# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Eco-Lens, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email the maintainers with details of the vulnerability.
3. Include steps to reproduce, impact assessment, and any suggested fixes.
4. You will receive an acknowledgment within 48 hours.

## Security Measures

### Environment & Secrets
- All API keys and secrets are stored in `.env` files, which are **never committed** to version control.
- `.env.example` contains only placeholder values — no real credentials.
- Security keys are auto-rotated via `autoconfig.bat` / `autoconfig.sh` using cryptographic random generation.

### API Security
- **Security Headers Middleware**: HSTS, X-Frame-Options (DENY), X-Content-Type-Options, X-XSS-Protection, strict Referrer-Policy, restrictive Permissions-Policy.
- **API Key Middleware**: Optional API key validation on protected endpoints via `X-API-Key` header.
- **CORS**: Restricted to configured frontend origin only.
- **Input Validation**: All API inputs are validated through Pydantic models with strict type checking.
- **SQL Injection Prevention**: All database queries use parameterized statements via SQLAlchemy.

### Frontend Security
- No secrets are embedded in client-side code.
- `NEXT_PUBLIC_*` environment variables contain only non-sensitive configuration (URLs).
- Content Security Policy headers are set by the backend middleware.

### Dependencies
- Dependabot is enabled for automated dependency updates.
- CI pipeline validates builds on every push and pull request.

### Data Privacy
- The application processes simulated traffic data in demo mode.
- No personally identifiable information (PII) is collected or stored.
- Camera feeds (when enabled) are processed in-memory and not persisted.
