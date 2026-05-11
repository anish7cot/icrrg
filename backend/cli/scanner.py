"""Scanner module — posts diffs to the SecureDiff API and renders results."""

from __future__ import annotations

import textwrap
import time
from pathlib import Path

import click
import httpx

from cli.cache import check_cache, write_cache
from cli.config import BlockingPolicy, load_config
from cli.token_store import load_token, load_refresh_token, save_token

# Timeout budget for hook scans (seconds).  Task-02 mandates < 2 s round-trip
# for the PHI / secret detection path (no LLM).
_HOOK_TIMEOUT = 10.0  # generous — network + cold-start; the 2 s target is e2e

# Polling settings for waiting on LLM review completion
_POLL_INTERVAL = 3.0  # seconds between polls
_POLL_MAX_WAIT = 120.0  # max seconds to wait for LLM review


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
    wait_for_llm: bool = False,
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
        # Auto-refresh on 401 (expired access token)
        if resp.status_code == 401:
            new_token = _try_refresh_token(api_url)
            if new_token:
                headers = {"Authorization": f"Bearer {new_token}"}
                resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
            else:
                click.secho(
                    "Session expired. Run `icrrg login` to re-authenticate.",
                    fg="red",
                    err=True,
                )
                return 1
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
    scan_status: str = data.get("status", "completed")
    scan_id: str | None = data.get("id")

    # ── show initial (rule-based) findings ────────────────────────────
    if findings:
        _print_findings(findings, risk_score, policy)
    _print_elapsed(elapsed)

    # ── wait for LLM review if requested ─────────────────────────────
    if wait_for_llm and scan_id and scan_status == "reviewing":
        llm_findings, llm_risk, llm_synthesis = _poll_for_llm_review(
            api_url, scan_id, headers
        )
        if llm_findings is not None:
            # LLM may have found additional issues beyond rule-based ones
            new_llm = [
                f for f in llm_findings
                if f.get("finding_type", "").startswith("llm:")
            ]
            if new_llm:
                click.secho(
                    f"\n[LLM Review] {len(new_llm)} additional finding(s) from AI analysis:\n",
                    fg="cyan",
                    bold=True,
                )
                _print_findings(new_llm, llm_risk, policy)
            elif not findings:
                click.secho("[OK] LLM review complete — no additional issues.", fg="green")

            # Use the full findings list for blocking decision
            findings = llm_findings
            risk_score = llm_risk

            if llm_synthesis:
                _print_synthesis(llm_synthesis)
    elif not findings:
        click.secho("[OK] No issues found.", fg="green")
        write_cache(repo_root, diff_text, clean=True)
        return 0

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

    if not findings:
        click.secho("[OK] No issues found.", fg="green")
        write_cache(repo_root, diff_text, clean=True)
        return 0

    click.secho(
        "[WARN] Findings detected but none are blocking. Commit allowed.",
        fg="yellow",
    )
    write_cache(repo_root, diff_text, clean=True)
    return 0


# ── token refresh ────────────────────────────────────────────────────

def _try_refresh_token(api_url: str) -> str | None:
    """Attempt to refresh the access token using the stored refresh token.

    Returns the new access token on success, None on failure.
    """
    refresh = load_refresh_token()
    if not refresh:
        return None

    url = f"{api_url}/api/v1/auth/refresh"
    try:
        resp = httpx.post(url, json={"refresh_token": refresh}, timeout=10.0)
        if resp.status_code != 200:
            return None
        data = resp.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
        if new_access:
            save_token(new_access, new_refresh)
            return new_access
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    return None


# ── LLM polling ──────────────────────────────────────────────────────

def _poll_for_llm_review(
    api_url: str,
    scan_id: str,
    headers: dict,
) -> tuple[list[dict] | None, float, dict | None]:
    """Poll GET /api/v1/scans/{scan_id} until status != 'reviewing'.

    Returns (findings, risk_score, synthesis_json) or (None, 0, None) on failure.
    """
    url = f"{api_url}/api/v1/scans/{scan_id}"
    waited = 0.0

    click.secho(
        "\n⏳ Waiting for LLM review to complete...", fg="cyan", nl=False
    )

    while waited < _POLL_MAX_WAIT:
        time.sleep(_POLL_INTERVAL)
        waited += _POLL_INTERVAL
        click.echo(".", nl=False)  # progress dots

        try:
            resp = httpx.get(url, headers=headers, timeout=10.0)
            resp.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            continue  # retry on transient errors

        data = resp.json()
        status = data.get("status", "")

        if status in ("completed", "failed"):
            click.echo()  # newline after dots
            elapsed = f"{waited:.0f}s"
            if status == "completed":
                click.secho(f"  LLM review completed ({elapsed})", fg="green", dim=True)
            else:
                click.secho(f"  LLM review failed ({elapsed})", fg="yellow", dim=True)
            return (
                data.get("findings", []),
                data.get("risk_score", 0),
                data.get("synthesis_json"),
            )

    click.echo()  # newline after dots
    click.secho(
        f"  LLM review timed out after {_POLL_MAX_WAIT:.0f}s. "
        "Check the dashboard for full results.",
        fg="yellow",
    )
    return None, 0, None


def _print_synthesis(synthesis: dict) -> None:
    """Render the Level-4 risk synthesis summary."""
    rating = synthesis.get("overall_risk_rating", "unknown")
    summary = synthesis.get("executive_summary", "")
    recs = synthesis.get("architectural_recommendations", [])

    color = "red" if rating in ("critical", "high") else "yellow" if rating == "medium" else "green"
    click.secho(f"\n── Risk Synthesis (Level 4) ──", bold=True)
    click.secho(f"  Overall Risk: {rating.upper()}", fg=color, bold=True)
    if summary:
        click.echo(textwrap.indent(summary, "  "))
    if recs:
        click.secho("  Recommendations:", bold=True)
        for r in recs:
            click.echo(f"    • {r}")
    click.echo()


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
