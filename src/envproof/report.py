"""Human-readable reports for issue trackers and terminal output."""

from __future__ import annotations

import json
from typing import Any


def _bullet(value: Any) -> str:
    return str(value).replace("\n", " ").replace("\r", " ")


def render_findings(findings: list[dict[str, Any]], *, title: str = "EnvProof findings") -> str:
    if not findings:
        return f"{title}\n{'=' * len(title)}\nNo diagnostic differences were found in the captured evidence.\n"
    counts = {level: sum(item.get("severity") == level for item in findings) for level in ("high", "warning", "info")}
    lines = [
        title,
        "=" * len(title),
        f"Findings: {len(findings)} (high: {counts['high']}, warning: {counts['warning']}, info: {counts['info']})",
        "",
    ]
    for index, finding in enumerate(findings, 1):
        lines.extend(
            [
                f"{index}. [{str(finding.get('severity', 'info')).upper()}] "
                f"{finding.get('summary', finding.get('code', 'Finding'))}",
                f"   Rule: {finding.get('code', 'UNKNOWN')}",
            ]
        )
        for evidence in finding.get("evidence", []):
            lines.append(f"   Evidence: {_bullet(evidence)}")
        if finding.get("explanation"):
            lines.append(f"   Why it matters: {_bullet(finding['explanation'])}")
        if finding.get("next_step"):
            lines.append(f"   Suggested next step: {_bullet(finding['next_step'])}")
        lines.append("")
    lines.append(
        "These are evidence-backed clues, not proof of root cause. "
        "Reproduce or test each hypothesis before changing code."
    )
    return "\n".join(lines).rstrip() + "\n"


def render_markdown_report(snapshot: dict[str, Any], *, max_packages: int = 60) -> str:
    """Render a shareable report without environment-variable values or source content."""
    python = snapshot.get("python", {})
    platform_info = snapshot.get("platform", {})
    project = snapshot.get("project", {})
    paths = snapshot.get("paths", {})
    privacy = snapshot.get("privacy", {})
    packages = snapshot.get("packages", [])
    modules = snapshot.get("modules", [])
    git = project.get("git", {})
    files = project.get("files", [])

    lines = [
        "# EnvProof diagnostic report",
        "",
        f"- Captured: `{snapshot.get('captured_at', 'unknown')}`",
        f"- EnvProof schema: `{snapshot.get('schema_version', 'unknown')}`",
        "",
        "## Runtime",
        "",
        f"- Python: `{python.get('version', 'unknown')}` ({python.get('implementation', 'unknown')})",
        f"- Virtual environment: `{python.get('is_venv', 'unknown')}`",
        f"- Executable: `{python.get('executable', 'unknown')}`",
        f"- Platform: `{platform_info.get('system', 'unknown')} {platform_info.get('release', '')}` / `{platform_info.get('machine', 'unknown')}`",
        f"- ABI / SOABI: `{python.get('soabi') or 'not reported'}`",
        "",
        "## Project evidence",
        "",
        f"- Project root: `{project.get('root', '$PROJECT')}` (redacted)",
        f"- Git repository detected: `{git.get('in_repo', 'not checked')}`",
        f"- Tracked working tree dirty: `{git.get('dirty', 'not checked')}`",
        f"- Manifest/config files fingerprinted: `{len(files)}`",
        "",
    ]
    if git.get("commit"):
        lines.append(f"- Commit (included by explicit request): `{git['commit']}`")
        lines.append("")
    if files:
        lines.extend(["| File | State | Size | SHA-256 |", "|---|---|---:|---|"])
        for item in files:
            name = _bullet(item.get("name", "unknown")).replace("|", "\\|")
            size = item.get("size_bytes", "—")
            digest = item.get("sha256", "—")
            lines.append(f"| `{name}` | `{item.get('status', 'unknown')}` | {size} | `{digest}` |")
        lines.append("")
    else:
        lines.extend(["No recognized project manifests were fingerprinted.", ""])

    flags = snapshot.get("environment", {}).get("flags", {})
    present = sorted(name for name, exists in flags.items() if exists)
    lines.extend(
        [
            "## Environment signals",
            "",
            f"- Relevant variable names present: {', '.join(f'`{name}`' for name in present) if present else 'none of the tracked names'}",
            "- Variable values are deliberately omitted.",
            f"- PATH entries: `{paths.get('path_entry_count', 0)}`",
            f"- `sys.path` entries: `{len(paths.get('sys_path', []))}`",
            "",
        ]
    )

    lines.extend(["## Import-resolution checks", ""])
    if modules:
        lines.extend(["| Module | Found | Origin kind | Origin |", "|---|---:|---|---|"])
        for module in modules:
            name = _bullet(module.get("name", "unknown")).replace("|", "\\|")
            origin = _bullet(module.get("origin") or "—").replace("|", "\\|")
            lines.append(
                f"| `{name}` | {module.get('found', False)} | `{module.get('origin_kind', 'unknown')}` | `{origin}` |"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "No specific imports were requested. Capture again with `--module package_name` to check import resolution.",
                "",
            ]
        )

    lines.extend(["## Installed distributions", "", f"Total distribution records: **{len(packages)}**", ""])
    if packages:
        visible = packages[: max(0, max_packages)]
        lines.extend(["| Distribution | Version | Location kind |", "|---|---|---|"])
        for package in visible:
            name = _bullet(package.get("name", "unknown")).replace("|", "\\|")
            version = _bullet(package.get("version", "unknown")).replace("|", "\\|")
            kind = _bullet(package.get("location_kind", "unknown")).replace("|", "\\|")
            lines.append(f"| `{name}` | `{version}` | `{kind}` |")
        if len(packages) > len(visible):
            lines.append("")
            lines.append(
                f"*Showing {len(visible)} of {len(packages)} distribution records; "
                "the JSON snapshot contains the full inventory.*"
            )
        lines.append("")
    else:
        lines.extend(["No installed distributions were recorded.", ""])

    lines.extend(
        [
            "## Privacy notes",
            "",
            f"- Environment-variable values included: `{privacy.get('environment_values_included', False)}`",
            f"- Source-file contents included: `{privacy.get('source_file_contents_included', False)}`",
            f"- Network requests made during capture: `{privacy.get('network_requests_made', False)}`",
            "- Known home, project, virtual-environment and base-interpreter roots are redacted where possible.",
            "- Review this report before sharing: distribution names, versions, path suffixes, platform details "
            "and manifest hashes can still disclose project information.",
            "",
            "---",
            "Generated by EnvProof. Environment differences are clues, not a guaranteed root-cause diagnosis.",
            "",
        ]
    )
    return "\n".join(lines)


def render_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
