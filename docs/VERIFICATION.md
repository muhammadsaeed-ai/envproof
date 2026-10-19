# Verification report

This report records checks actually run for the `0.1.0` local release candidate. Passing local checks do not prove cross-platform support, clean remote CI, third-party security-audit status, or PyPI publication.

## Environment

- Date: 2026-10-19
- Local interpreter: CPython 3.13.5
- Local operating system: Linux container, `Linux-6.18.55-x86_64-with-glibc2.41`
- Runtime dependencies: none
- Remote GitHub Actions: the repository is now public; CI/security workflows are triggered by the initial source push and remain unverified until their runs finish.
- Network limitation: the Python package index could not be resolved from this environment, so Ruff, mypy, Twine, `build`, and `pip-audit` could not be installed for local verification.

## Executed checks

| Check | Command / method | Result |
|---|---|---|
| Syntax compilation | `python -m compileall -q src tests examples benchmarks` | **PASS** |
| Unit/integration suite | `/tmp/envproof-final-venv/bin/python -m unittest discover -s tests -v` with the built wheel installed and no `PYTHONPATH` override | **PASS: 44 tests in 0.250 seconds** (final installed wheel in isolated venv, no `PYTHONPATH` override) |
| Source suite in current review environment | `PYTHONPATH=src python -m pytest -q` | **PASS: 44 tests in 4.77 seconds** |
| Editable install retry in current review environment | `python -m pip install -e . --no-deps` | **BLOCKED**; the isolated build tried to fetch `setuptools>=77`, but the package index was unreachable |
| Clean isolated install | `python -m pip install --no-index --no-deps dist/envproof-0.1.0-py3-none-any.whl` in a new virtual environment | **PASS**; no runtime dependencies needed |
| Installed entry point | `envproof --version`, `envproof --help`, and all four subcommand help screens | **PASS** |
| Dependency consistency | `/tmp/envproof-final-venv/bin/python -m pip check` | **PASS: no broken requirements** |
| Package build | `setuptools.build_meta.build_wheel('dist')` and `build_sdist('dist')` | **PASS**; wheel and source distribution created |
| Source distribution usability | System Python `python -m pip wheel --no-index --no-deps --no-build-isolation dist/envproof-0.1.0.tar.gz -w /tmp/envproof-sdist-wheel` | **PASS**; source archive produced a wheel without fetching packages |
| End-to-end CLI smoke | Capture two isolated project fixtures, compare JSON with `--fail-on warning`, and render Markdown | **PASS**; one expected finding, compare exit code `1`, report file created |
| Controlled differentiator demo | `PYTHONPATH=src python examples/demo_drift.py` | **PASS**; detected changed `requirements.txt` and asserted `PROJECT_MANIFEST_CHANGED` |
| Capture/compare smoke benchmark | `python benchmarks/benchmark_capture.py` using the installed wheel | **PASS**; final run recorded below |
| Ruff lint / formatter | `python -m ruff check ...`; `python -m ruff format --check ...` | **NOT RUN**; Ruff unavailable and package index DNS failed |
| Mypy | `python -m mypy src/envproof` | **NOT RUN**; mypy unavailable and package index DNS failed |
| Twine metadata validation | `python -m twine check dist/*` | **NOT RUN**; Twine unavailable and package index DNS failed |
| Dependency vulnerability audit | `python -m pip_audit` / configured CI job | **NOT RUN**; pip-audit unavailable and package index DNS failed |
| Python 3.10–3.14 and Windows/macOS matrix | GitHub Actions workflow | **PENDING REMOTE CI**; confirm all jobs on the public repository before release |

The final wheel and source distribution were rebuilt after the reliability changes using the installed `setuptools` PEP 517 backend because the `build` frontend could not be installed. The rebuilt wheel was reinstalled into an isolated virtual environment; its CLI and all 44 unit/integration tests passed. The source distribution also produced a wheel offline with the system Python build backend. This is not a substitute for `twine check` or a complete publishing pipeline.

## Single-run benchmark observation

Three single-run smoke observations were recorded on CPython 3.13.5 / Linux. In the full host environment (508 distribution records), capture took about 0.236 seconds and comparison about 0.0015 seconds. In an earlier clean installed-wheel run (2 distribution records), capture took about 0.025 seconds and comparison about 0.000067 seconds; in the final rerun from the rebuilt 0.1.0 wheel (2 distribution records), capture took 0.020861 seconds and comparison 0.000066 seconds. Each run used one project manifest and two import probes, and each detected a deliberately injected Python-version difference. These environments have different inventory sizes and the observations are not a comparative performance claim, a statistical benchmark, or a guarantee about larger projects.

## Security and quality findings

- Snapshot loading is bounded to 20 MiB before JSON parsing, then schema-validated; JSON is treated as data, not executable content.
- Manifest fingerprint reading is bounded to 5 MiB even if the underlying file changes after its initial metadata check.
- Output is written to a same-directory temporary file, flushed, and atomically published. Existing output is refused unless `--force` is supplied; on filesystems without hard-link support, safe no-clobber publication returns an actionable error.
- Environment-variable values and source-file contents are not serialized by capture. Known path roots are redacted where possible, but reports can still reveal distribution names, version numbers, path suffixes, platform facts, or manifest hashes. Review any artifact before sharing.
- Git integration uses fixed, read-only commands with `shell=False` and timeouts. Untracked files are not included in the dirty-state indicator. Commit hashes are opt-in.
- No third-party security scan, external penetration test, or formal privacy certification was performed. Those remain release gates.

## Release decision

The source repository is published, but the release should remain a **release candidate** until Ruff, mypy, Twine, dependency auditing, and the declared remote OS/Python CI matrix run successfully. No GitHub Release/tag or PyPI package has been published by this source push.
