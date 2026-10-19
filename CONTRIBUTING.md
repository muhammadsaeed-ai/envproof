# Contributing to EnvProof

Thanks for considering a contribution. Small, reproducible and well-tested changes are preferred over broad feature bundles.

## Before opening an issue

- Search existing issues for a duplicate.
- Include Python version, operating system and the EnvProof version.
- For a bug, include the exact command and a small synthetic project/snapshot that reproduces it.
- Review every snapshot before sharing it. Do not attach source code, real `.env` files, tokens, private package-index URLs or confidential package names.

## Development setup

```bash
python -m venv .venv
# Activate the environment
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m ruff check src tests examples benchmarks
python -m ruff format --check src tests examples benchmarks
python -m mypy src/envproof
```

## Contribution expectations

- Add tests for normal, boundary and failure cases.
- New diagnostic rules must show exactly which captured evidence triggers them.
- Do not assert causality where only correlation was observed.
- Do not add network calls, telemetry, environment-value capture, or source-file collection without a documented security review and explicit user control.
- Keep runtime dependencies at zero unless there is a clear, reviewed benefit.
- Update the docs and `CHANGELOG.md` for user-visible behavior changes.
- Preserve compatibility with the current snapshot schema or propose a schema-version change.
- Format the code, run tests, lint and type checks, and explain any checks you could not execute.

## Pull requests

PRs should describe the user problem, the implementation decision, verification commands/results, platform coverage, security/privacy impact and documentation changes. Avoid drive-by refactors in the same PR as a behavioral change.

## Architecture review

Please discuss major schema or privacy changes before implementation. Snapshot schema changes can affect stored evidence; runtime dependencies and data collection require explicit justification.
