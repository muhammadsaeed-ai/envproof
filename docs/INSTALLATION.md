# Installation and usage

## Requirements

- Python 3.10 or newer.
- Supported intent: Windows, macOS, and Linux. The initial CI matrix tests common hosted runners; exact behavior still depends on interpreter and host configuration.
- No mandatory third-party runtime packages.

## Install from source

The public source repository is available at `https://github.com/muhammadsaeed-ai/envproof`. Clone it with the commands below.

```bash
git clone https://github.com/muhammadsaeed-ai/envproof.git
cd envproof
python -m venv .venv
```

Activate `.venv`; on PowerShell use `.\.venv\Scripts\Activate.ps1`, and on macOS/Linux use `source .venv/bin/activate`. Then:

```bash
python -m pip install .
envproof --version
```

For development, use `python -m pip install -e ".[dev]"`.

## Capture

```bash
envproof capture . --output envproof.json --module json --module requests
```

- `--output` / `-o`: destination path. Existing files require `--force`.
- `--module`: a valid top-level Python import name. Repeat for more probes.
- `--include-commit`: opt in to including the current Git commit hash.
- `--no-git`: skip Git detection and dirty-state commands.

## Audit

```bash
envproof audit . --module json --format text
envproof audit . --module requests --format json --output audit.json
envproof audit . --fail-on warning
```

`audit` captures evidence in memory and applies the local rule set. `--fail-on warning` is intended for an explicitly configured CI gate, not as the default.

## Compare

Capture the baseline and current snapshots from their respective environments, then move them through your approved secure channel:

```bash
envproof compare baseline.json current.json
envproof compare baseline.json current.json --format markdown --output drift.md
envproof compare baseline.json current.json --format json --output drift.json --fail-on high
```

The left snapshot is treated as the known-good baseline; the right snapshot is the environment being investigated. Package-added/removed findings are relative to that direction.

## Export a report

```bash
envproof report envproof.json --format markdown --output report.md
envproof report envproof.json --format json --output normalized.json
```

Markdown report output limits distribution rows to 60 by default. Use `--max-packages 0` to omit the package table; a JSON report retains the complete inventory.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Command succeeded and any configured failure threshold was not met |
| `1` | Findings met `--fail-on warning` or `--fail-on high` |
| `2` | Invalid invocation, invalid input, unsupported snapshot schema, or expected operation error |
| `130` | Interrupted by the user |

## Interpreting findings

- **High**: a plausible major contributor, such as different Python minor versions, implementations, or requested import origins.
- **Warning**: a potentially meaningful difference that deserves investigation.
- **Info**: context that may be useful but is lower-confidence or often expected.

Severity is deterministic rule metadata, not a statistical probability. Always verify a cause by reproducing the problem or running a controlled test.

## Troubleshooting

**`Output already exists`** — choose a new output path or pass `--force` after confirming you intend to replace the file.

**`Unsupported schema_version`** — use a EnvProof version that understands the snapshot schema or recapture with the currently installed version. Do not manually rewrite the schema version.

**Import probe says not found** — confirm the active interpreter and install the package in that interpreter. Try running `python -c "import sys; print(sys.executable); print(sys.path)"` in the same shell. EnvProof intentionally does not import a target module during a probe.

**Paths differ** — review venv activation, working directory, editable installs, PYTHONPATH and system-site-packages. Do not remove packages or directories based only on a diagnostic hint.

**Private path still appears** — redaction is best-effort. Remove or redact sensitive fields manually before sharing, or file an issue using a synthetic snapshot.
