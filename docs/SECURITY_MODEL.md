# Security and privacy model

## Threat model

EnvProof may be run in private repositories, virtual environments with credentials configured in the shell, and machines where the project or dependency metadata is not intended for public release. A snapshot may later be attached to a public issue. The priority is minimizing collection and avoiding execution of project code from untrusted paths.

## What is collected

- Python/runtime version, implementation, executable/prefix identities, ABI metadata, and OS/architecture facts.
- Sanitized search paths and a short summary of PATH resolution.
- Names, versions and install-location metadata from installed Python distribution records.
- A fixed list of project manifest names with status, size and SHA-256.
- Presence-only signals for a small allowlist of environment-variable names.
- Optional import origins for explicitly requested valid top-level module names.
- Git repository detection and tracked dirty/clean status. Commit hash only with `--include-commit`.

## What is not collected

- Environment-variable values.
- Source contents, `.env` files, README bodies, arbitrary configuration contents, or log files.
- Git diff contents or changed file names.
- Network data, telemetry, remote API calls or uploaded artifacts.
- Credentials from direct URL metadata; package direct URLs are not copied.

## Executed operations

- Snapshot capture reads runtime metadata and selected known manifest files.
- SHA-256 hashing is limited to recognized manifest/config files and files no larger than 5 MiB each.
- Distribution metadata is capped at 50,000 records.
- Snapshot input is capped at 20 MiB.
- Import inspection is limited to valid top-level names and uses import finders. It does not import the selected module or execute its body.
- Optional Git checks run fixed arguments with `shell=False`, no stdin and a two-second per-command timeout. They disable `core.fsmonitor` for the invocation and set `GIT_OPTIONAL_LOCKS=0`. A failed status check is recorded as unknown, not clean. No arbitrary user command is intentionally executed.

## Residual risks and limitations

- Privacy cannot be guaranteed. Names/versions of dependencies, manifest hashes, OS release, path suffixes and optional commit hashes can reveal private project facts. Redaction recognizes common roots but cannot infer every organization's naming conventions.
- Python's import system can contain custom meta-path finders with side effects. EnvProof uses standard finders for top-level resolution rather than general `find_spec`, but it is not a formal sandbox for a hostile interpreter process.
- Python distribution metadata may be malformed or deceptive. EnvProof reports it as environment evidence; it does not authenticate package origin.
- Git installations can have local configuration. The commands are fixed and use no shell, but the host's Git executable/configuration remains part of the trusted environment.
- Snapshot hashes are not signatures or attestations. They do not prove the integrity of source or installed dependencies.
- Untrusted snapshot files can contain misleading values. They are validated as JSON and never execute code, but their findings should not be trusted without review.
- Output path access is governed by the user's operating-system permissions. Do not write reports into shared directories unless that is intended.

## Safe reporting guidance

1. Run capture locally; do not pipe snapshots to an unknown remote service.
2. Review Markdown and JSON before sharing, especially package names, private paths and manifest hashes.
3. Use `--no-git` to disable Git checks, or omit `--include-commit` to keep commit hashes out.
4. Do not add code to EnvProof that uploads artifacts by default.
5. For public bug reports, prefer minimized examples and synthetic snapshots; never attach real secrets or private `.env` files.

## Dependency security

The installed package has no third-party runtime dependencies. Build and development tools are optional and separated from runtime. CI installs the development extras for lint, type and test checks. A `pip-audit` workflow is configured for pushes, pull requests and weekly scheduled runs. Its security result cannot be described as passing until the workflow has executed on the remote repository; no scanner badge is included before that point.

## Reporting a vulnerability

Please follow `SECURITY.md`. Do not publish exploitation details or sensitive snapshots in a public issue.
