# EnvProof product specification (v0.1.0)

## Problem statement

When a Python project fails in one environment but works in another, the developer or maintainer may need to gather runtime versions, interpreter locations, package inventories, import paths, OS details and project dependency metadata from separate commands. This creates friction and makes comparisons inconsistent.

## Target users

- Python maintainers triaging reports that they cannot reproduce.
- Developers comparing local and CI / staging environments.
- Platform engineers investigating interpreter and dependency drift.
- Library maintainers who need reviewable, privacy-conscious diagnostic artifacts.

## Primary use cases

1. Run `envproof audit` to surface common interpreter/path configuration hazards.
2. Capture a snapshot in a known-good environment and another in a failing environment.
3. Compare snapshots to narrow the investigation using evidence-ranked findings.
4. Attach a reviewed Markdown report to an issue or internal incident.
5. Gate CI on high-severity or warning-level drift when a project explicitly wants that policy.

## v0.1 requirements and acceptance criteria

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-01 | Capture Python/runtime metadata | Snapshot reports Python version tuple/string, implementation, executable/prefix identities, venv state, ABI/SOABI, platform and architecture. |
| FR-02 | Capture distribution inventory | Installed distribution name/version/location metadata are sorted deterministically and bounded to 50,000 records. |
| FR-03 | Fingerprint project manifests | Recognized manifest/config files are stored as names, size/status and SHA-256; file contents are never embedded. |
| FR-04 | Record import-origin evidence | Explicit top-level names are resolved without executing the target module; dotted names and invalid identifiers return a clear error. |
| FR-05 | Privacy-first environment metadata | Only presence flags for an allowlist are captured; environment values and dotenv contents do not appear in output. |
| FR-06 | Compare snapshots | Version, implementation, platform, sys.path, environment flags, distributions, manifest hashes, import origins and Git state can produce findings. |
| FR-07 | Explain diagnostic findings | Each finding has a stable rule code, severity, evidence, explanation and next step. |
| FR-08 | Usable output | CLI supports terminal output plus JSON and Markdown; JSON snapshots are versioned. |
| FR-09 | Safety and validation | JSON input is size bounded, schema checked and never deserialized through an executable format. File overwrite requires explicit `--force`. |
| FR-10 | Non-destructive capture | Capture does not install dependencies, alter project files, contact the network or execute arbitrary commands. |
| FR-11 | CI integration | `--fail-on never|warning|high` yields predictable exit codes. |
| FR-12 | Package quality | Source distribution/wheel build; CLI entry point; automated tests; GitHub Actions checks. |

## Non-functional requirements

- **Python support:** Python 3.10 through 3.14 intended in v0.1.0 CI.
- **Runtime dependencies:** none.
- **Network:** no network requests from product runtime.
- **Privacy:** no telemetry, no environment values, no project source contents.
- **Performance:** normal capture should finish in seconds on typical developer environments; large package inventories are bounded.
- **Resilience:** malformed distribution metadata should not necessarily abort the complete capture; impossible/unsafe operations return actionable errors.
- **Portability:** POSIX and Windows paths are normalized through the standard library; full local verification is reported separately from CI matrix coverage.
- **Determinism:** lists and findings have explicit stable sort rules; timestamps and runtime facts naturally vary between captures.

## Out of scope for v0.1.0

- Automated root-cause claims or AI-generated fixes.
- Executing a failing command or arbitrary project code.
- Full import tracing, profiling or coverage analysis.
- GPU/driver/native-library audits.
- Network tests, secrets scanning, arbitrary configuration-file parsing, or full manifest semantic parsing.
- Packaging a whole project or minimizing a reproduction.
- Hosted dashboards, telemetry, accounts or paid API integrations.

## User journey

1. Install EnvProof in the intended diagnostic interpreter.
2. Run `envproof audit . --module package_name` for local clues.
3. Capture a baseline on a known-good machine/CI job.
4. Capture an incident snapshot with the same selected module names.
5. Compare baseline and incident snapshots; inspect high-severity findings first.
6. Verify a suggested cause using a controlled experiment before changing dependencies/code.
7. Review the generated report for proprietary names, version data and path suffixes before sharing.

## Success metrics to collect only after release

- Time from install to first useful finding in real incident reports.
- Fraction of snapshots that identify a difference confirmed by the maintainer.
- False-positive / unhelpful-finding rates by diagnostic rule.
- Successful installation and CLI usage in Python 3.10–3.14 CI.
- External issues/PRs that reproduce a bug or contribute a tested rule.

No telemetry is included; these metrics must be gathered through voluntary issue feedback or contributor reports.
