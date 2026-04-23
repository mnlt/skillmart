#!/usr/bin/env python3
"""Integration tests for teleport telemetry.

Runs each flow in a sandboxed $HOME, triggers the event, and diffs the counter
endpoint to confirm the event fired. Tests 7 of 8 telemetry events — skill-used
requires a live Claude Code session and is documented as manual.

Tests increment real production counters at https://teleport.mnlt.deno.net.
Cheap and maintainer-only for now, so minor noise is acceptable.

Run from repo root:
    python3 tests/test_telemetry.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

COUNTER_URL = "https://teleport.mnlt.deno.net"
INSTALL_SH_URL = "https://raw.githubusercontent.com/mnlt/teleport/main/setup/install.sh"
# KV eventual consistency grace period. Increase if tests flake.
SETTLE_SECONDS = 3


# ---------- helpers ----------

def get_stats() -> dict:
    with urllib.request.urlopen(f"{COUNTER_URL}/stats", timeout=10) as r:
        return json.loads(r.read())


def diff(before: dict, after: dict, key: str) -> int:
    return int(after.get(key, 0)) - int(before.get(key, 0))


def sandbox_env(tmpdir: Path) -> dict:
    """Env with $HOME overridden; PATH has the sandboxed teleport-setup."""
    env = os.environ.copy()
    env["HOME"] = str(tmpdir)
    env["PATH"] = f"{tmpdir}/.local/bin:{env.get('PATH', '')}"
    # Tests pollute the real counter. If you ever want to silence telemetry for a run,
    # uncomment: env["TELEPORT_NO_TELEMETRY"] = "1"
    return env


def run_install(tmpdir: Path) -> subprocess.CompletedProcess:
    """Fetch the live install.sh and run it with HOME=tmpdir."""
    script = tmpdir / "_install.sh"
    subprocess.run(
        ["curl", "-sSfL", INSTALL_SH_URL, "-o", str(script)],
        check=True, timeout=30,
    )
    return subprocess.run(
        ["bash", str(script)],
        env=sandbox_env(tmpdir), capture_output=True, text=True, timeout=300,
    )


def run_cli(tmpdir: Path, *args, stdin=None) -> subprocess.CompletedProcess:
    """Run teleport-setup inside the sandbox."""
    bin_path = tmpdir / ".local" / "bin" / "teleport-setup"
    return subprocess.run(
        [str(bin_path), *args],
        env=sandbox_env(tmpdir), capture_output=True, text=True,
        input=stdin, timeout=60,
    )


def write_claude_config(tmpdir: Path, mcps: dict) -> None:
    """Write a fake ~/.claude.json with given MCPs under the sandbox's project scope."""
    config = {"projects": {str(tmpdir): {"mcpServers": mcps}}}
    (tmpdir / ".claude.json").write_text(json.dumps(config, indent=2))


# ---------- tests ----------

def test_install_events() -> tuple[str, bool, str]:
    name = "install-started + install-completed"
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        before = get_stats()
        proc = run_install(tmpdir)
        time.sleep(SETTLE_SECONDS)
        after = get_stats()
        started = diff(before, after, "install-started")
        completed = diff(before, after, "install-completed")
        ok = proc.returncode == 0 and started >= 1 and completed >= 1
        detail = f"rc={proc.returncode} started=+{started} completed=+{completed}"
        if not ok:
            detail += f"\n  stderr tail: {proc.stderr[-400:]}"
        return name, ok, detail


def test_first_run_detect_migration() -> tuple[str, bool, str]:
    name = "first-run + mcp-detected + migration"
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        install_proc = run_install(tmpdir)
        if install_proc.returncode != 0:
            return name, False, f"install failed: {install_proc.stderr[-400:]}"

        # Fake config with two MCPs — github has creds in env (ready to migrate),
        # figma has creds too (another ready migration). Both are in mcp-knowledge
        # so classify() will route them correctly.
        write_claude_config(tmpdir, {
            "github": {
                "type": "stdio", "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "ghp_faketoken1234567890"},
            },
            "figma": {
                "type": "stdio", "command": "npx",
                "args": ["-y", "figma-developer-mcp"],
                "env": {"FIGMA_ACCESS_TOKEN": "figd_faketoken1234"},
            },
        })

        before = get_stats()
        proc = run_cli(tmpdir, "--yes")
        time.sleep(SETTLE_SECONDS)
        after = get_stats()

        first_run = diff(before, after, "first-run")
        gh_det = diff(before, after, "mcp-detected/github")
        fg_det = diff(before, after, "mcp-detected/figma")
        migration = diff(before, after, "migration")

        ok = first_run >= 1 and gh_det >= 1 and fg_det >= 1 and migration >= 1
        detail = (f"rc={proc.returncode} first-run=+{first_run} "
                  f"mcp-detected/github=+{gh_det} mcp-detected/figma=+{fg_det} "
                  f"migration=+{migration}")
        if not ok:
            detail += f"\n  stdout: {proc.stdout[-400:]}\n  stderr: {proc.stderr[-400:]}"
        return name, ok, detail


def test_add_key() -> tuple[str, bool, str]:
    name = "add-key-started + add-key-completed"
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        install_proc = run_install(tmpdir)
        if install_proc.returncode != 0:
            return name, False, f"install failed: {install_proc.stderr[-400:]}"

        # Empty config — add-key doesn't need pre-existing MCPs
        write_claude_config(tmpdir, {})

        before = get_stats()
        proc = run_cli(
            tmpdir, "add-key", "github", "--from-stdin", "--no-browser",
            stdin="ghp_faketoken1234567890\n",
        )
        time.sleep(SETTLE_SECONDS)
        after = get_stats()

        started = diff(before, after, "add-key-started/github")
        completed = diff(before, after, "add-key-completed/github")
        ok = started >= 1 and completed >= 1
        detail = f"rc={proc.returncode} started=+{started} completed=+{completed}"
        if not ok:
            detail += f"\n  stdout: {proc.stdout[-400:]}\n  stderr: {proc.stderr[-400:]}"
        return name, ok, detail


# ---------- runner ----------

TESTS = [test_install_events, test_first_run_detect_migration, test_add_key]


def main() -> int:
    print(f"counter endpoint: {COUNTER_URL}")
    print(f"running {len(TESTS)} test(s). each takes 30-90s (real install in sandbox).\n")

    results = []
    for fn in TESTS:
        print(f"▸ {fn.__name__}...")
        try:
            results.append(fn())
        except Exception as e:
            results.append((fn.__name__, False, f"exception: {e}"))
        print(f"  {results[-1][2]}\n")

    print("=== Summary ===")
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\n{passed}/{len(results)} passed")
    print("\nNote: skill-used event requires a live Claude Code session (not tested here).")
    print("      Verify manually: ask Claude 'use teleport' with a known intent, then check /stats.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
