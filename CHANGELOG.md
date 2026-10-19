# Changelog

All notable changes to EnvProof will be recorded here.

## [0.1.0] - 2026-10-19

Initial release candidate:

- Capture a versioned JSON snapshot of Python runtime, platform, import paths, distribution metadata, project-manifest hashes, selected environment presence flags, optional import origins and Git state.
- Compare two snapshots with stable, evidence-backed findings and severity levels.
- Audit a live snapshot for common interpreter/path configuration hazards.
- Render Markdown and JSON reports.
- Add privacy-by-default behavior, bounded inputs, schema validation, non-destructive file output, unit/end-to-end tests, and cross-platform CI configuration.

The source code is available in the public GitHub repository. A GitHub Release/tag and PyPI distribution are separate release steps and have not been published by this source push.
