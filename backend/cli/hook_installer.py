"""Install / uninstall the SecureDiff pre-commit hook."""

import os
import platform
import stat
import sys
from pathlib import Path

import click

# The hook script is written with LF line endings only (critical for
# cross-platform compatibility — CRLF breaks shell execution on Mac/Linux).
_HOOK_MARKER = "# --- SecureDiff pre-commit hook ---"


def _resolve_git_dir(repo_path: str) -> Path:
    """Return the .git/hooks directory, raising if not a git repo."""
    git_dir = Path(repo_path).resolve() / ".git"
    if not git_dir.is_dir():
        click.secho(
            f"Not a git repository: {Path(repo_path).resolve()}", fg="red", err=True
        )
        sys.exit(1)
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    return hooks_dir


def _to_posix_path(win_path: str) -> str:
    """Convert a Windows path to a POSIX-style path for Git Bash.

    Example: C:\\Users\\name\\project → /c/Users/name/project
    On non-Windows systems this is a no-op.
    """
    if platform.system() != "Windows":
        return win_path
    # Replace backslashes with forward slashes
    p = win_path.replace("\\", "/")
    # Convert drive letter: C:/... → /c/...
    if len(p) >= 2 and p[1] == ":":
        p = "/" + p[0].lower() + p[2:]
    return p


def _build_hook_script(api_url: str) -> str:
    """Return the shell script content for the pre-commit hook."""
    # Use absolute path to the CLI so the hook works from any working directory.
    # The hook invokes `icrrg scan` via Python module execution.
    python_executable = sys.executable  # absolute path to current Python
    # The cli package lives inside the backend/ directory — set PYTHONPATH so
    # Python can resolve `cli.main` regardless of the shell's cwd.
    backend_dir = _to_posix_path(str(Path(__file__).resolve().parent.parent))
    python_path = _to_posix_path(python_executable)

    script = (
        "#!/bin/sh\n"
        f"{_HOOK_MARKER}\n"
        "#\n"
        "# Installed by: icrrg install\n"
        "# This hook scans staged changes for secrets, PHI, and code issues.\n"
        "#\n"
        "\n"
        "# ── Skip during rebase ──────────────────────────────────────────\n"
        "# Rebase replays commits; scanning each one wastes 20+ seconds.\n"
        'GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)\n'
        'if [ -n "$GIT_REBASE_TODO" ] || '
        '[ -d "$GIT_DIR/rebase-merge" ] || '
        '[ -d "$GIT_DIR/rebase-apply" ]; then\n'
        '  echo "SecureDiff: rebase detected — skipping scan."\n'
        "  exit 0\n"
        "fi\n"
        "\n"
        "# ── Skip during merge ───────────────────────────────────────────\n"
        "# Merged code was already committed elsewhere; no need to re-scan.\n"
        'if [ -f "$GIT_DIR/MERGE_HEAD" ]; then\n'
        '  echo "SecureDiff: merge commit detected — skipping scan."\n'
        "  exit 0\n"
        "fi\n"
        "\n"
        "# Grab the staged diff\n"
        'DIFF=$(git diff --cached)\n'
        "\n"
        '# Nothing staged? Allow commit.\n'
        'if [ -z "$DIFF" ]; then\n'
        "  exit 0\n"
        "fi\n"
        "\n"
        f'export SECUREDIFF_API_URL="{api_url}"\n'
        'export SECUREDIFF_REPO_DIR="$(pwd)"\n'
        "\n"
        "# cd to backend dir so Python can find the cli package\n"
        f'cd "{backend_dir}"\n'
        "\n"
        "# Run the SecureDiff CLI scanner\n"
        f'"{python_path}" -m cli.main scan\n'
        "exit $?\n"
    )
    return script


def install_hook(repo_path: str, api_url: str) -> None:
    """Write the pre-commit hook into the target repo."""
    hooks_dir = _resolve_git_dir(repo_path)
    hook_file = hooks_dir / "pre-commit"

    # Check for existing hook that isn't ours
    if hook_file.exists():
        existing = hook_file.read_text(encoding="utf-8", errors="replace")
        if _HOOK_MARKER in existing:
            click.secho("SecureDiff hook already installed — updating.", fg="yellow")
        else:
            click.secho(
                "A pre-commit hook already exists and was NOT created by SecureDiff.\n"
                "Remove it manually or back it up before installing.",
                fg="red",
                err=True,
            )
            sys.exit(1)

    script = _build_hook_script(api_url)

    # Write with LF line endings (binary mode) to avoid CRLF on Windows
    hook_file.write_bytes(script.encode("utf-8"))

    # Make executable (no-op on Windows but required for Mac/Linux)
    hook_file.chmod(hook_file.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    click.secho(
        f"✔ Pre-commit hook installed → {hook_file}",
        fg="green",
        bold=True,
    )
    click.echo(f"  API endpoint: {api_url}")
    click.echo("  Run `icrrg uninstall` to remove it.")


def uninstall_hook(repo_path: str) -> None:
    """Remove the SecureDiff pre-commit hook."""
    hooks_dir = _resolve_git_dir(repo_path)
    hook_file = hooks_dir / "pre-commit"

    if not hook_file.exists():
        click.secho("No pre-commit hook found — nothing to remove.", fg="yellow")
        return

    content = hook_file.read_text(encoding="utf-8", errors="replace")
    if _HOOK_MARKER not in content:
        click.secho(
            "The existing pre-commit hook was NOT installed by SecureDiff. "
            "Leaving it untouched.",
            fg="yellow",
        )
        return

    hook_file.unlink()
    click.secho("✔ SecureDiff pre-commit hook removed.", fg="green", bold=True)
