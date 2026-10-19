# First-release checklist

## Repository identity

- [x] Publish the source tree to `https://github.com/muhammadsaeed-ai/envproof` on the `main` branch as a public repository.
- [ ] Confirm repository description and topics are configured as intended; review branch protection and security settings.
- [ ] Verify the MIT license choice and author/copyright line.
- [ ] Enable branch protection if the repository owner plans to accept contributions.
- [ ] Enable private vulnerability reporting in repository settings if available.

## Quality gates

- [ ] Clean virtual environment installation and `envproof --version` succeed.
- [ ] Full unit/integration suite succeeds on the release commit.
- [ ] Ruff lint/format and mypy complete successfully.
- [ ] sdist/wheel build succeeds and `twine check dist/*` passes.
- [ ] CI passes for the advertised Python/OS matrix; do not infer matrix success from a local run.
- [ ] Dependency audit has no unresolved high/critical advisories relevant to packaged dependencies.
- [ ] Review generated JSON/Markdown and confirm no credentials/private data are present.
- [ ] Verify snapshot size caps, path redaction, atomic no-clobber output, and untrusted snapshot validation.
- [ ] Run the reproducible drift demo and record actual observed findings.

## Publishing

- [ ] Create a release tag `v0.1.0` only after all gates pass.
- [ ] Attach source archive and wheel generated from the exact tag if distributing release assets.
- [ ] Publish to PyPI only after configuring Trusted Publishing or another reviewed credential method.
- [ ] Never put PyPI API tokens in the repository, logs, or checked-in workflow.
- [ ] Do not add status badges until workflows have actually run and badge URLs are correct.
- [ ] Add an announcement with a concrete sample workflow, limitations, and a request for reproducible feedback.

## Launch follow-through

- [ ] Open focused issues for known limitations and milestones, not a long list of speculative features.
- [ ] Ask a small group of Python maintainers to test captures on real incidents.
- [ ] Track first-success rate, confirmed findings, false positives and user-reported time saved without adding telemetry.
- [ ] Review dependency/OS support at least quarterly and update the support policy.
