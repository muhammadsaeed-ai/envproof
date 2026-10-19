# Security policy

## Supported versions

Security fixes are targeted at the latest released EnvProof version. During the initial alpha period, users should upgrade to the latest available release before reporting a vulnerability.

## Reporting a vulnerability

Please do not publish potentially exploitable details or sensitive snapshots in a public GitHub issue. Use GitHub’s **Report a vulnerability** workflow on the repository’s Security tab if it is enabled. Otherwise, contact the repository maintainer privately using an available contact method on GitHub. Do not assume private vulnerability reporting is enabled until you verify the repository settings.

## Scope

Security-relevant reports include environment data leakage, arbitrary code execution during snapshot loading or import probing, path traversal, unbounded resource use, unsafe file overwrites, and dependency/build issues affecting users.

## Snapshot handling

Treat snapshots and reports as potentially sensitive despite the default redactions. They can contain package inventories, platform information, path suffixes, manifest hashes and optional commit hashes. Do not place real captures in public issue fixtures without review.
