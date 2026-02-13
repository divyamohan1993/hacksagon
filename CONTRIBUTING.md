# Contributing to Eco-Lens

Thank you for your interest in contributing to Eco-Lens!

## Development Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure API keys
3. Run `setup.bat` (Windows) or `setup.sh` (Linux/Mac)
4. Start backend: `cd backend && python -m uvicorn main:app --reload --port 8000`
5. Start frontend: `cd frontend && npm run dev`

## Project Structure

```
hacksagon/
├── backend/          # FastAPI backend (Python 3.11+)
│   ├── services/     # Core scientific engines
│   ├── api/          # REST + WebSocket handlers
│   └── data/         # EPA emission factors
├── frontend/         # Next.js 14 dashboard (TypeScript)
│   └── src/
│       ├── components/  # React components
│       ├── hooks/       # Custom hooks
│       └── lib/         # Utilities
├── docs/             # Documentation
└── .github/          # CI/CD workflows
```

## Code Standards

- **Python:** Follow PEP 8, type hints encouraged
- **TypeScript:** Strict mode, no `any` types
- **Commits:** Use conventional commit messages

## Reporting Issues

Open an issue with reproduction steps and environment details.
