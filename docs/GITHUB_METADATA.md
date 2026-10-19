# GitHub launch metadata

## Repository description

Privacy-conscious Python environment snapshots and explainable drift diagnostics for debugging "works on my machine" failures.

## Suggested topics

`python`, `python3`, `developer-tools`, `debugging`, `environment-diagnostics`, `reproducibility`, `cli`, `python-packaging`, `dependency-diagnostics`, `privacy`, `ci-cd`, `open-source`.

## Suggested first issues

1. **Rule-quality feedback:** add a synthetic case for one observed false-positive or missing signal, with expected finding code and severity.
2. **Platform regression case:** reproduce a path-classification difference on Windows/macOS and add a platform-neutral test fixture.
3. **Manifest allowlist proposal:** show a specific common manifest that materially helps Python troubleshooting, and explain why hashing its name/size/content digest is safe and worth supporting.
4. **Compatibility matrix audit:** confirm supported Python versions against actual CI results and update classifiers only after evidence exists.
5. **Report sanitization review:** supply a synthetic example showing a path shape that current best-effort redaction misses.

These are candidate issues based on explicit limits in v0.1, not reports from users. Open only the issues that would help real contributors, using clear `good first issue` and `help wanted` labels where appropriate.

## Contributor first task

A first-time contributor should be able to clone the repo, install `.[dev]`, run the unit suite, read `docs/ARCHITECTURE.md`, and add a rule plus a deterministic test without needing any token or paid service.
