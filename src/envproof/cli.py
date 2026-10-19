"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from envproof import __version__
from envproof._output import atomic_write_text
from envproof.capture import capture_snapshot, load_snapshot, write_snapshot
from envproof.compare import compare_snapshots, fail_level
from envproof.diagnostics import audit_snapshot
from envproof.errors import EnvProofError
from envproof.report import render_findings, render_json, render_markdown_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envproof",
        description="Capture and compare privacy-conscious Python environment diagnostics.",
        epilog="Environment values and source-file contents are never included in snapshots.",
    )
    parser.add_argument("--version", action="version", version=f"EnvProof {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="Capture a JSON snapshot of a Python environment and project.")
    capture.add_argument(
        "project", nargs="?", default=".", help="Project directory to fingerprint (default: current directory)."
    )
    capture.add_argument("-o", "--output", default="envproof-snapshot.json", help="Snapshot JSON output path.")
    capture.add_argument(
        "--module",
        action="append",
        default=[],
        help="Top-level module whose import origin should be recorded; repeatable.",
    )
    capture.add_argument(
        "--include-commit", action="store_true", help="Include the Git commit hash. Off by default for privacy."
    )
    capture.add_argument("--no-git", action="store_true", help="Do not run read-only Git state checks.")
    capture.add_argument("--force", action="store_true", help="Replace the output file if it already exists.")

    compare = subparsers.add_parser("compare", help="Compare a known-good baseline snapshot with a current snapshot.")
    compare.add_argument("baseline", help="Known-good baseline EnvProof JSON snapshot.")
    compare.add_argument("current", help="Current or failing EnvProof JSON snapshot.")
    compare.add_argument(
        "--format", choices=("text", "markdown", "json"), default="text", help="Report format (default: text)."
    )
    compare.add_argument("--output", "-o", help="Write report to a file instead of stdout.")
    compare.add_argument("--force", action="store_true", help="Replace report output if it already exists.")
    compare.add_argument(
        "--fail-on",
        choices=("never", "warning", "high"),
        default="never",
        help="Exit with status 1 when findings reach this severity.",
    )

    audit = subparsers.add_parser("audit", help="Check the current environment for known configuration hazards.")
    audit.add_argument(
        "project", nargs="?", default=".", help="Project directory to inspect (default: current directory)."
    )
    audit.add_argument(
        "--module",
        action="append",
        default=[],
        help="Top-level module whose import origin should be checked; repeatable.",
    )
    audit.add_argument(
        "--include-commit",
        action="store_true",
        help="Include the Git commit hash in internal evidence; off by default.",
    )
    audit.add_argument("--no-git", action="store_true", help="Do not run read-only Git state checks.")
    audit.add_argument(
        "--format", choices=("text", "markdown", "json"), default="text", help="Report format (default: text)."
    )
    audit.add_argument("--output", "-o", help="Write report to a file instead of stdout.")
    audit.add_argument("--force", action="store_true", help="Replace report output if it already exists.")
    audit.add_argument(
        "--fail-on",
        choices=("never", "warning", "high"),
        default="never",
        help="Exit with status 1 when findings reach this severity.",
    )

    report = subparsers.add_parser("report", help="Render a stored snapshot as a Markdown report or normalized JSON.")
    report.add_argument("snapshot", help="EnvProof JSON snapshot.")
    report.add_argument(
        "--format", choices=("markdown", "json"), default="markdown", help="Report format (default: markdown)."
    )
    report.add_argument("--output", "-o", help="Write report to a file instead of stdout.")
    report.add_argument("--force", action="store_true", help="Replace report output if it already exists.")
    report.add_argument(
        "--max-packages", type=int, default=60, help="Maximum distributions in Markdown output (default: 60)."
    )
    return parser


def _write_text(text: str, output: str | None, *, force: bool = False) -> None:
    if output is None or output == "-":
        sys.stdout.write(text)
        return
    atomic_write_text(output, text, force=force, label="report")


def _summary(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(findings),
        "high": sum(item.get("severity") == "high" for item in findings),
        "warning": sum(item.get("severity") == "warning" for item in findings),
        "info": sum(item.get("severity") == "info" for item in findings),
    }


def _report_findings(
    findings: list[dict[str, Any]],
    *,
    mode: str,
    context: dict[str, Any] | None = None,
    fmt: str,
) -> str:
    document: dict[str, Any] = {"mode": mode, "summary": _summary(findings), "findings": findings}
    if context:
        document["context"] = context
    if fmt == "json":
        return render_json(document)
    if fmt == "markdown":
        title = "EnvProof local audit" if mode == "audit" else "EnvProof environment comparison"
        body_lines = render_findings(findings, title=title).splitlines()[2:]
        lines = [f"# {title}", ""]
        if context and "python" in context:
            py = context["python"]
            lines.extend([f"Python: {py.get('version', 'unknown')} ({py.get('implementation', 'unknown')})", ""])
        lines.extend(body_lines)
        return "\n".join(lines).rstrip() + "\n"
    title = "EnvProof local audit" if mode == "audit" else "EnvProof environment comparison"
    return render_findings(findings, title=title)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # Keep ``main([...])`` composable in tests and embedding code while the
        # console-script wrapper still receives the usual integer exit status.
        return int(exc.code or 0)
    try:
        if args.command == "capture":
            snapshot = capture_snapshot(
                args.project,
                modules=args.module,
                include_commit=args.include_commit,
                include_git=not args.no_git,
            )
            target = write_snapshot(snapshot, args.output, force=args.force)
            print(f"Snapshot written: {target}")
            print(
                f"Captured {len(snapshot['packages'])} distribution records and "
                f"{len(snapshot['modules'])} import-resolution checks."
            )
            print("Privacy defaults: environment values and source-file contents were not captured.")
            return 0

        if args.command == "compare":
            baseline = load_snapshot(args.baseline)
            current = load_snapshot(args.current)
            findings = compare_snapshots(baseline, current)
            output = _report_findings(findings, mode="compare", fmt=args.format)
            _write_text(output, args.output, force=args.force)
            return 1 if fail_level(findings, args.fail_on) else 0

        if args.command == "audit":
            snapshot = capture_snapshot(
                args.project,
                modules=args.module,
                include_commit=args.include_commit,
                include_git=not args.no_git,
            )
            findings = audit_snapshot(snapshot)
            context = {"python": snapshot["python"], "platform": snapshot["platform"]}
            output = _report_findings(findings, mode="audit", context=context, fmt=args.format)
            _write_text(output, args.output, force=args.force)
            return 1 if fail_level(findings, args.fail_on) else 0

        if args.command == "report":
            if args.max_packages < 0:
                raise EnvProofError("--max-packages must be zero or greater.")
            snapshot = load_snapshot(args.snapshot)
            if args.format == "json":
                output = render_json(snapshot)
            else:
                output = render_markdown_report(snapshot, max_packages=args.max_packages)
            _write_text(output, args.output, force=args.force)
            return 0

        parser.error(f"Unknown command: {args.command}")
        return 2
    except EnvProofError as exc:
        print(f"envproof: error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0
    except KeyboardInterrupt:
        print("envproof: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
