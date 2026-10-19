# Release announcement draft — EnvProof v0.1.0

**Title:** EnvProof v0.1.0: compare Python environments with evidence, not guesswork

When a Python application works on one machine and fails on another, the first step is often a scattered set of commands: check Python, inspect pip, print `sys.path`, inspect package versions, and compare dependency files manually.

EnvProof packages those clues into a reviewable snapshot, then compares a known-good environment with an incident environment. Findings include the exact observed difference, why it may matter, and a concrete next investigation step.

What makes the first release useful:

- A standard-library-only runtime with no required AI key, account, telemetry or network service.
- Versioned JSON snapshots plus terminal, Markdown and JSON diagnostic output.
- Python/runtime, installed-distribution, `sys.path`, requested import-origin, manifest-fingerprint and Git-state comparisons.
- Explicit privacy limits: environment-variable values and source-file contents are never serialized by the capture engine.
- CI-friendly exit thresholds and a reproducible local demo.

EnvProof does not prove root cause, recreate an environment or guarantee that a bug is environmental. Its findings are clues to validate. Snapshots can still contain sensitive package names, versions, path suffixes and hashes, so review them before sharing.

Try the quick-start commands in the README, run `python examples/demo_drift.py`, and share a synthetic reproduction or rule-quality feedback. Early testers are especially valuable for identifying false positives and missing environment signals.

**Repository:** https://github.com/muhammadsaeed-ai/envproof

**Version:** 0.1.0 (alpha)

**Package distribution:** source/wheel publication is a separate action and should be announced only after it has succeeded.
