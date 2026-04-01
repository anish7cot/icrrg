"""Scanner module — posts diffs to the SecureDiff API and renders results."""

from __future__ import annotations

import textwrap
import time
from pathlib import Path

import click
import httpx

from cli.cache import check_cache, write_cache
from cli.config import BlockingPolicy, load_config
from cli.token_store import load_token

# Timeout budget for hook scans (seconds).  Task-02 mandates < 2 s round-trip
# for the PHI / secret detection path (no LLM).
_HOOK_TIMEOUT = 10.0  # generous — network + cold-start; the 2 s target is e2e


# ── severity colours ─────────────────────────────────────────────────
_SEVERITY_COLOR: dict[str, str] = {
    "CRITICAL": "red",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "white",
}


def submit_scan(
    api_url: str,
    diff_text: str,
    repo_name: str = "cli-scan",
    timeout: float = _HOOK_TIMEOUT,
    repo_root: str | Path | None = None,
) -> int:
    """POST the diff to the scan API, print results, return exit code (0 or 1).

    * Returns **0** when there are no blocking findings (commit allowed).
    * Returns **1** when blocking-severity findings are detected (commit blocked).
    * Returns **0** when the backend is unreachable (graceful skip).
    """
    policy = load_config(repo_root)

    # ── amend cache: skip re-scan if diff is identical to last clean scan ──
    cached = check_cache(repo_root, diff_text)
    if cached is True:
        click.secho("[OK] No issues found (cached - diff unchanged).", fg="green")
        return 0
    if cached is False:
        click.secho("[BLOCKED] Previous scan had blocking findings (cached).", fg="red")
        return 1

    url = f"{api_url}/api/v1/scans"
    payload = {"diff_text": diff_text, "repository": repo_name}

    # Require authentication
    token = load_token()
    if not token:
        click.secho(
            "Not authenticated. Run `icrrg login` or `icrrg register` first.",
            fg="red",
            err=True,
        )
        return 1
    headers = {"Authorization": f"Bearer {token}"}

    start = time.monotonic()

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException):
        # Backend not reachable — allow the commit so devs aren't blocked
        click.secho(
            "ICRRG backend not reachable, skipping scan.",
            fg="yellow",
            err=True,
        )
        return 0
    except httpx.HTTPStatusError as exc:
        click.secho(
            f"API error: {exc.response.status_code} — skipping scan.",
            fg="yellow",
            err=True,
        )
        return 0

    elapsed = time.monotonic() - start
    data = resp.json()

    findings: list[dict] = data.get("findings", [])
    risk_score: float = data.get("risk_score", 0)

    if not findings:
        click.secho("[OK] No issues found.", fg="green")
        _print_elapsed(elapsed)
        write_cache(repo_root, diff_text, clean=True)
        return 0

    # ── render findings ──────────────────────────────────────────────
    _print_findings(findings, risk_score, policy)
    _print_elapsed(elapsed)

    # ── decide block / allow based on policy ─────────────────────────
    blocked_findings = [
        f for f in findings if policy.is_blocking(f.get("severity", ""))
    ]

    if blocked_findings:
        # Summarise by severity:  "2 critical, 1 high"
        counts: dict[str, int] = {}
        for f in blocked_findings:
            sev = f.get("severity", "unknown").lower()
            counts[sev] = counts.get(sev, 0) + 1
        summary = ", ".join(f"{n} {s}" for s, n in counts.items())

        click.secho(
            f"COMMIT BLOCKED: {summary} finding(s).",
            fg="red",
            bold=True,
        )
        write_cache(repo_root, diff_text, clean=False)
        return 1

    click.secho(
        "[WARN] Findings detected but none are blocking. Commit allowed.",
        fg="yellow",
    )
    write_cache(repo_root, diff_text, clean=True)
    return 0


# ── pretty-printing helpers ──────────────────────────────────────────

def _print_findings(
    findings: list[dict], risk_score: float, policy: BlockingPolicy
) -> None:
    """Render a colour-coded list of findings to the terminal."""
    header_color = "red" if risk_score >= 7 else "yellow"
    click.secho(
        f"\n[!] {len(findings)} finding(s) - risk score: {risk_score:.1f}/10\n",
        fg=header_color,
        bold=True,
    )
    for f in findings:
        severity = f.get("severity", "unknown").upper()
        ftype = f.get("finding_type", "")
        fpath = f.get("file_path", "<unknown>")
        line = f.get("line_number", "?")
        msg = f.get("message", "")
        color = _SEVERITY_COLOR.get(severity, "white")

        # Action tag based on policy
        action = policy.action_for(severity.lower())
        if action == "block":
            tag = click.style(" BLOCK ", fg="white", bg="red", bold=True)
        elif action == "warn":
            tag = click.style(" WARNING ", fg="black", bg="yellow", bold=True)
        else:
            tag = click.style(" info ", dim=True)

        click.echo(f"  {tag} ", nl=False)
        click.secho(f"[{severity}] ", fg=color, nl=False, bold=True)
        click.echo(f"{ftype} — {fpath}:{line}")
        if msg:
            click.echo(textwrap.indent(msg, "    "))

    click.echo()


def _print_elapsed(elapsed: float) -> None:
    """Show scan round-trip time (dimmed)."""
    click.secho(f"  scan completed in {elapsed:.2f}s", dim=True)
