# EnvProof Source Repository Inventory

This public GitHub repository contains the EnvProof v0.1.0 source tree, project metadata, GitHub templates and workflows, documentation, examples, tests, and benchmark script.

## Repository contents

- `.editorconfig`
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/dependabot.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/security.yml`
- `.gitignore`
- `CHANGELOG.md`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `MANIFEST.in`
- `README.md`
- `SECURITY.md`
- `SUPPORT.md`
- `benchmarks/benchmark_capture.py`
- `docs/ARCHITECTURE.md`
- `docs/COMPLETION_REPORT.md`
- `docs/DEMO_SCRIPT.md`
- `docs/GITHUB_METADATA.md`
- `docs/INSTALLATION.md`
- `docs/RELEASE_ANNOUNCEMENT.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/RESEARCH.md`
- `docs/SECURITY_MODEL.md`
- `docs/SPECIFICATION.md`
- `docs/VERIFICATION.md`
- `examples/demo_drift.py`
- `pyproject.toml`
- `src/envproof/`
- `tests/`

## Intentionally excluded from Git

The generated `dist/` wheel and source archive are not committed because `dist/` is excluded by `.gitignore`. Generate release artifacts from the reviewed commit and attach them to a GitHub Release only after the CI and package-validation gates pass. The original complete ZIP bundle includes the prebuilt artifacts and its checksum manifest.

Git history is created by GitHub during publication; the supplied ZIP itself is a portable bundle, not a clone.
