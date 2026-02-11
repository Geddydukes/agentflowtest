# API Stability Policy

AgentFT follows semantic versioning (`MAJOR.MINOR.PATCH`).

- `PATCH`: Backward-compatible bug fixes only.
- `MINOR`: New backward-compatible features.
- `MAJOR`: Backward-incompatible API changes.

## Public API Surface

Public API is limited to symbols exported in `src/agentft/__init__.py` and CLI commands documented in `README.md`.

## Deprecation Lifecycle

1. Introduce deprecation warning in a `MINOR` release.
2. Keep deprecated API for at least one full `MINOR` release cycle.
3. Remove in the next `MAJOR` release.

## Compatibility Guarantees

- Run artifacts keep schema version tags.
- Breaking artifact schema changes require migration tooling.
- CLI commands preserve flag semantics within major versions.
