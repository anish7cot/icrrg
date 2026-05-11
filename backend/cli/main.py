"""SecureDiff CLI — pre-commit hook installer and manual scanner."""

import os
import re
import subprocess
import sys

import click
import httpx

from cli.token_store import save_token, load_token, load_refresh_token, clear_token


def _detect_repo_name(git_cmd: list[str]) -> str | None:
    """Try to extract the repository name from the git remote URL.

    Supports HTTPS and SSH remote formats:
      https://github.com/owner/repo.git  → owner/repo
      git@github.com:owner/repo.git      → owner/repo
    """
    result = subprocess.run(
        [*git_cmd, "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    url = result.stdout.strip()
    # SSH: git@github.com:owner/repo.git
    m = re.match(r"git@[^:]+:(.+?)(\.git)?$", url)
    if m:
        return m.group(1).rsplit("/", 1)[-1]
    # HTTPS: https://github.com/owner/repo.git
    m = re.match(r"https?://[^/]+/(.+?)(\.git)?$", url)
    if m:
        return m.group(1).rsplit("/", 1)[-1]
    return None

DEFAULT_API_URL = "http://localhost:8000"


@click.group()
@click.option(
    "--api-url",
    envvar="SECUREDIFF_API_URL",
    default=DEFAULT_API_URL,
    help="Base URL of the SecureDiff API server.",
)
@click.pass_context
def cli(ctx: click.Context, api_url: str) -> None:
    """SecureDiff (icrrg) — scan diffs for secrets, PHI, and code-quality issues."""
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url.rstrip("/")


# ── login / logout ───────────────────────────────────────────────────


@cli.command()
@click.option("--username", prompt=True, help="Your ICRRG username.")
@click.option("--password", prompt=True, hide_input=True, help="Your ICRRG password.")
@click.pass_context
def login(ctx: click.Context, username: str, password: str) -> None:
    """Authenticate with the ICRRG backend and store the token."""
    api_url = ctx.obj["api_url"]
    url = f"{api_url}/api/v1/auth/login"
    try:
        resp = httpx.post(url, json={"username": username, "password": password}, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", "Login failed")
        click.secho(f"Login failed: {detail}", fg="red", err=True)
        sys.exit(1)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        click.secho("Cannot reach ICRRG backend.", fg="red", err=True)
        sys.exit(1)

    data = resp.json()
    token_path = save_token(data["access_token"], data.get("refresh_token"))
    click.secho(f"✔ Logged in as {username}", fg="green", bold=True)
    click.echo(f"  Token saved to {token_path}")


@cli.command()
def logout() -> None:
    """Remove stored ICRRG credentials."""
    clear_token()
    click.secho("✔ Logged out.", fg="green")


@cli.command()
@click.option("--username", prompt=True, help="Choose a username.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Choose a password.")
@click.pass_context
def register(ctx: click.Context, username: str, password: str) -> None:
    """Create a new ICRRG account and store the token."""
    api_url = ctx.obj["api_url"]
    url = f"{api_url}/api/v1/auth/register"
    try:
        resp = httpx.post(url, json={"username": username, "password": password}, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("detail", "Registration failed")
        click.secho(f"Registration failed: {detail}", fg="red", err=True)
        sys.exit(1)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        click.secho("Cannot reach ICRRG backend.", fg="red", err=True)
        sys.exit(1)

    data = resp.json()
    token_path = save_token(data["access_token"], data.get("refresh_token"))
    click.secho(f"✔ Registered and logged in as {username}", fg="green", bold=True)
    click.echo(f"  Token saved to {token_path}")


# ── install / uninstall ──────────────────────────────────────────────
from cli.hook_installer import install_hook, uninstall_hook  # noqa: E402


@cli.command()
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True),
    help="Path to the git repository (default: current directory).",
)
@click.pass_context
def install(ctx: click.Context, repo: str) -> None:
    """Install the SecureDiff pre-commit hook into a git repository."""
    api_url = ctx.obj["api_url"]
    install_hook(repo, api_url)


@cli.command()
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True),
    help="Path to the git repository (default: current directory).",
)
def uninstall(repo: str) -> None:
    """Remove the SecureDiff pre-commit hook from a git repository."""
    uninstall_hook(repo)


# ── scan (manual one-shot) ───────────────────────────────────────────
from cli.scanner import submit_scan  # noqa: E402


@cli.command()
@click.option(
    "--repo-name",
    default=None,
    help="Repository name sent with the scan request (auto-detected from git remote if omitted).",
)
@click.option(
    "--wait/--no-wait",
    default=None,
    help="Wait for LLM review to complete before exiting. Default: wait for manual scans, skip for pre-commit hooks.",
)
@click.pass_context
def scan(ctx: click.Context, repo_name: str | None, wait: bool | None) -> None:
    """Run a scan on the currently staged diff (git diff --cached)."""
    api_url = ctx.obj["api_url"]

    # When invoked from the hook, the original repo dir is saved in this env var
    # because the hook does `cd` to the backend dir for Python imports.
    repo_dir = os.environ.get("SECUREDIFF_REPO_DIR")
    git_cmd = ["git", "-C", repo_dir] if repo_dir else ["git"]

    # Pre-commit hooks (SECUREDIFF_REPO_DIR set) must return fast so VS Code's
    # Source Control UI doesn't hang.  Rule-based engines already catch secrets
    # and PHI immediately; LLM findings appear in the dashboard afterwards.
    # Manual `icrrg scan` waits for LLM by default.
    if wait is None:
        wait = repo_dir is None  # True for manual scan, False for hooks

    # Discover the repo root so we can read .icrrg.yml
    root_result = subprocess.run(
        [*git_cmd, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    repo_root = root_result.stdout.strip() if root_result.returncode == 0 else None

    # Auto-detect repo name from git remote if not explicitly provided
    if repo_name is None:
        repo_name = _detect_repo_name(git_cmd) or "cli-scan"

    # Get staged diff
    result = subprocess.run(
        [*git_cmd, "diff", "--cached"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        click.secho("Failed to run git diff --cached", fg="red", err=True)
        sys.exit(1)

    diff_text = result.stdout
    if not diff_text.strip():
        click.secho("No staged changes found.", fg="yellow")
        sys.exit(0)

    exit_code = submit_scan(
        api_url, diff_text, repo_name, repo_root=repo_root, wait_for_llm=wait
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
