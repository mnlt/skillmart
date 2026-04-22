#!/usr/bin/env python3
"""teleport-setup — detect installed MCPs and migrate them to teleport.

Modern interactive TUI using `rich` (colors) and `questionary` (arrow-key
multi-select). One command, one unified list, clear value proposition.

Usage:
  teleport-setup                  Interactive flow (list → select → confirm → apply)
  teleport-setup --scan           Read-only: print list and exit
  teleport-setup --yes            Non-interactive: migrate & remove all migratable
  teleport-setup --dry-run        Show plan without writing
  teleport-setup --keep-servers   Migrate credentials but DON'T remove MCP entries
"""

import argparse
import getpass
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

VERSION = "0.7.1"
CLAUDE_CONFIG = Path.home() / ".claude.json"
SETTINGS_LOCAL = Path.home() / ".claude" / "settings.local.json"
KNOWLEDGE_URL = "https://raw.githubusercontent.com/mnlt/teleport/main/mcp-knowledge.json"
TELEMETRY_URL = "https://teleport.goatcounter.com/count"
TELEMETRY_MARKER = Path.home() / ".teleport-venv" / ".first-run"


def telemetry_ping(path: str) -> None:
    """Anonymous event ping. Silent failure. Opt out: TELEPORT_NO_TELEMETRY=1."""
    if os.environ.get("TELEPORT_NO_TELEMETRY") == "1":
        return
    try:
        url = f"{TELEMETRY_URL}?p={path}&t={VERSION}"
        req = urllib.request.Request(url, headers={"User-Agent": f"teleport-setup/{VERSION}"})
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        pass


def telemetry_ping_once(path: str, marker: Path) -> None:
    """Ping only if the marker file doesn't exist. Creates marker on first ping."""
    if marker.exists():
        return
    telemetry_ping(path)
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except Exception:
        pass

# --- Rich + Questionary guard ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    import questionary
    from questionary import Style as QStyle
except ImportError as e:
    print(f"error: missing dependency — {e.name}")
    print()
    print("teleport-setup uses rich and questionary for its interface.")
    print("Install with:")
    print("  curl -sL https://raw.githubusercontent.com/mnlt/teleport/main/setup/install.sh | bash")
    sys.exit(2)

console = Console()

QS_STYLE = QStyle([
    # Semantic tokens — no full-background fills, hierarchy through fg intensity + weight
    ("qmark",       "fg:#22d3ee bold"),        # cyan accent marker
    ("question",    "bold"),                   # question text (no color bg)
    ("pointer",     "fg:#22d3ee bold"),        # ▸ cursor
    ("highlighted", "fg:#22d3ee noreverse"),   # hovered item — cyan fg only, no bg
    ("selected",    "fg:#4ade80 noreverse"),   # checked item — soft green fg only
    ("separator",   "fg:#374151"),
    ("instruction", "fg:#6b7280 italic"),
    ("answer",      "fg:#4ade80 bold"),
    ("disabled",    "fg:#4b5563 italic"),
    ("text",        ""),                       # default body text
])


# --- data loading ---

def load_knowledge(url_or_path: str) -> dict:
    if url_or_path.startswith("http"):
        with urllib.request.urlopen(url_or_path, timeout=10) as r:
            return json.load(r)
    with open(url_or_path) as f:
        return json.load(f)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def backup_file(path: Path) -> Path:
    if not path.exists():
        return None
    bak = path.parent / f"{path.name}.bak-{int(time.time())}"
    shutil.copy2(path, bak)
    return bak


# --- detection & classification ---

def detect_mcps(config: dict) -> list:
    results = []
    for scope, proj in config.get("projects", {}).items():
        for name, mcp in proj.get("mcpServers", {}).items():
            results.append((scope, name, mcp))
    return results


def classify(name: str, mcp_config: dict, knowledge: dict) -> tuple:
    npm_pkg = None
    for a in mcp_config.get("args", []):
        if isinstance(a, str) and a.startswith("@") and ("mcp" in a.lower() or "context" in a.lower()):
            npm_pkg = "@" + a.lstrip("@").split("@")[0]
            break
    for mcp_id, entry in knowledge.get("mcps", {}).items():
        if name == entry.get("mcp_server_default_name"):
            return mcp_id, entry
        if npm_pkg and entry.get("npm_package") and npm_pkg.rstrip("@").startswith(entry["npm_package"]):
            return mcp_id, entry
    return None, None


def extract_cred_from_mcp(mcp_config: dict, entry: dict) -> tuple:
    env_block = mcp_config.get("env", {})
    candidates = [entry.get("env_var")] + list(entry.get("alt_env_vars", []))
    for c in candidates:
        if c and env_block.get(c):
            return c, env_block[c]
    headers = mcp_config.get("headers", {})
    if isinstance(headers, dict):
        for k, v in headers.items():
            if isinstance(v, str) and v.startswith("Bearer "):
                return entry.get("env_var"), v[7:]
    return None, None


def build_plan(mcps: list, knowledge: dict, existing_env: dict, disabled_list_by_scope: dict) -> list:
    """Produce [{name, scope, status, ...}] for each detected MCP.

    Statuses:
      - ready:            Cat A, creds extractable, env var not set → migrate automatically
      - needs-setup:      Cat A, but no creds locally (OAuth-only or empty env) → add-key carousel
      - already-migrated: env var already present → info only (may already be disabled)
      - unsupported:      not in knowledge base or Cat B/C — can't teleport
    """
    plan = []
    for scope, name, mcp_config in mcps:
        is_disabled = name in disabled_list_by_scope.get(scope, [])
        mcp_id, entry = classify(name, mcp_config, knowledge)
        item = {"name": name, "scope": scope, "mcp_config": mcp_config, "disabled": is_disabled}
        if not entry:
            item.update({"status": "unsupported", "label": "not in teleport's knowledge base"})
            plan.append(item)
            continue
        item["mcp_id"] = mcp_id
        item["entry"] = entry
        item["baseline_tokens"] = entry.get("baseline_tokens", 0)
        category = entry.get("category")
        if category == "C":
            item.update({"status": "unsupported", "label": "requires local runtime"})
            plan.append(item)
            continue
        if category == "B":
            item.update({"status": "unsupported", "label": "redundant with built-in tools"})
            plan.append(item)
            continue
        env_var = entry.get("env_var")
        if env_var and existing_env.get(env_var):
            item.update({"status": "already-migrated", "env_var": env_var})
            plan.append(item)
            continue
        found_var, cred_value = extract_cred_from_mcp(mcp_config, entry)
        if cred_value:
            item.update({
                "status": "ready",
                "env_var": env_var,
                "cred_value": cred_value,
            })
        else:
            hint = "OAuth — needs API key" if entry.get("hosted_mcp_url") else f"needs {env_var}"
            item.update({
                "status": "needs-setup",
                "env_var": env_var,
                "setup_hint": hint,
            })
        plan.append(item)
    return plan


def get_disabled_mcps(config: dict) -> dict:
    """Returns {scope_path: [name, ...]} of disabled MCPs across all project scopes."""
    result = {}
    for scope, proj in config.get("projects", {}).items():
        disabled = proj.get("disabledMcpServers", [])
        if disabled:
            result[scope] = list(disabled)
    return result


def disable_mcp_in_config(config: dict, scope: str, name: str) -> bool:
    """Add MCP name to disabledMcpServers[] in claude.json for the given scope.
    Returns True if newly added, False if already disabled."""
    proj = config.setdefault("projects", {}).setdefault(scope, {})
    disabled = proj.setdefault("disabledMcpServers", [])
    if name in disabled:
        return False
    disabled.append(name)
    return True


# --- UI rendering ---

def fmt_tokens(n: int) -> str:
    """Returns e.g. '4k' or '650' — never prefixed with ~, callers add the tilde if they want."""
    if n >= 1000:
        return f"{n//1000}k"
    return str(n)


def row_right_text(item: dict) -> str:
    """Right column — context-aware short description."""
    s = item["status"]
    if s == "ready":
        return "[cyan]migrate + disable MCP[/cyan]"
    if s == "needs-setup":
        return f"[cyan]{item.get('setup_hint', 'needs key')}[/cyan]"
    if s == "already-migrated":
        return "[green]already on teleport[/green]" + (" [dim](disabled)[/dim]" if item.get("disabled") else "")
    if s == "unsupported":
        return f"[dim italic]{item.get('label', 'unsupported')}[/dim italic]"
    return ""


def print_header() -> None:
    """Subtle brand header — no box, just a title with accent."""
    console.print()
    console.print("  [bold]teleport[/bold] [dim]· migrate your Claude Code MCPs[/dim]")
    console.print()


def print_summary(plan: list) -> None:
    total = len(plan)
    ready = [p for p in plan if p["status"] == "ready"]
    setup = [p for p in plan if p["status"] == "needs-setup"]
    done = [p for p in plan if p["status"] == "already-migrated"]
    unsup = [p for p in plan if p["status"] == "unsupported"]

    parts = []
    if ready:
        parts.append(f"[cyan]{len(ready)} ready[/cyan]")
    if setup:
        parts.append(f"[cyan]{len(setup)} needs setup[/cyan]")
    if done:
        parts.append(f"[green]{len(done)} already on teleport[/green]")
    if unsup:
        parts.append(f"[dim]{len(unsup)} unsupported[/dim]")
    console.print(f"  [dim]▸ found[/dim] [bold]{total}[/bold] [dim]MCP{'s' if total != 1 else ''} —[/dim] " + " [dim]·[/dim] ".join(parts))
    console.print()


def print_list(plan: list) -> None:
    """Sectioned list: ready / needs-setup / already-migrated / unsupported."""
    if not plan:
        return

    name_width = max(len(p["name"]) for p in plan) + 2

    def section(title: str, items: list) -> None:
        if not items:
            return
        console.print(f"  [dim]── {title} ─────────────────────────────────────[/dim]")
        console.print()
        for item in items:
            console.print(f"    [bold]{item['name']:<{name_width}s}[/bold]  {row_right_text(item)}")
        console.print()

    ready = [p for p in plan if p["status"] == "ready"]
    setup = [p for p in plan if p["status"] == "needs-setup"]
    done = [p for p in plan if p["status"] == "already-migrated"]
    unsup = [p for p in plan if p["status"] == "unsupported"]

    section("ready to migrate", ready)
    section("needs setup (I'll walk you through each)", setup)
    section("already on teleport", done)
    section("unsupported", unsup)


# --- actions ---

def remove_mcp_from_config(config: dict, scope: str, name: str) -> bool:
    """Remove MCP entry from claude.json config dict in-place. Returns True if removed."""
    try:
        del config["projects"][scope]["mcpServers"][name]
        return True
    except KeyError:
        return False


def cmd_add_key(args: argparse.Namespace) -> int:
    """Guide user through adding an API key for a specific service."""
    if not ensure_claude_code_installed():
        return 1

    knowledge = load_knowledge(args.knowledge)
    mcps = knowledge.get("mcps", {})

    # If no service specified, list and prompt
    service = args.service
    if not service:
        if not sys.stdin.isatty():
            console.print("[red]error:[/red] `teleport-setup add-key` requires a service name (or a TTY).\n")
            console.print("Known services: " + ", ".join(f"[magenta]{k}[/magenta]" for k in sorted(mcps.keys())))
            return 2
        choices = [
            questionary.Choice(
                title=f"{k:<12s}  {mcps[k].get('friction_note', '')}",
                value=k,
            )
            for k in sorted(mcps.keys())
        ]
        service = questionary.select(
            "Which service?",
            choices=choices,
            style=QS_STYLE,
        ).ask()
        if not service:
            return 130

    if service not in mcps:
        console.print(f"[red]error:[/red] '[cyan]{service}[/cyan]' is not in teleport's knowledge base.")
        console.print("Known services: " + ", ".join(f"[magenta]{k}[/magenta]" for k in sorted(mcps.keys())))
        return 1

    entry = mcps[service]
    env_var = entry.get("env_var")
    signup_url = entry.get("signup_url")
    key_example = entry.get("key_example", "")
    friction_note = entry.get("friction_note", "")
    regex_str = entry.get("key_format_regex")
    multi_var = entry.get("multi_var", False)

    # ---- Auto-register shortcut ----
    # Services with auth_flow == "auto-register" have an endpoint that creates
    # an anonymous account and returns a key — no signup page, no paste.
    if entry.get("auth_flow") == "auto-register":
        register_url = entry["register_url"]
        register_body = entry.get("register_body", {})
        resp_key = entry.get("register_response_key", "api_key")
        console.print()
        console.print(Panel.fit(
            f"[bold]{entry.get('name', service)}[/bold]  [dim]— {entry.get('description', '')}[/dim]\n\n"
            f"  [dim]{friction_note}[/dim]",
            border_style="cyan"))
        console.print()
        console.print(f"[dim]Registering with {register_url}…[/dim]")
        try:
            req = urllib.request.Request(
                register_url,
                data=json.dumps(register_body).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                result = json.loads(r.read())
        except Exception as e:
            console.print(f"[red]error:[/red] registration failed: {e}")
            return 1
        value = result.get(resp_key)
        if not value:
            console.print(f"[red]error:[/red] no '{resp_key}' in response: {result}")
            return 1
        if regex_str and not re.match(regex_str, value):
            console.print(f"[yellow]warning:[/yellow] key '{value[:8]}…' doesn't match expected format")
        settings = load_json(SETTINGS_LOCAL)
        env_block = settings.setdefault("env", {})
        if env_block.get(env_var) == value:
            console.print(f"[dim]· {env_var} already set with this value. No changes.[/dim]")
            return 0
        bak = backup_file(SETTINGS_LOCAL)
        if bak:
            console.print(f"[dim]Backup: {bak}[/dim]")
        env_block[env_var] = value
        SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_LOCAL, "w") as f:
            json.dump(settings, f, indent=2)
        console.print()
        console.print(Panel.fit(
            f"[green bold]✓ {service} registered.[/green bold]\n\n"
            f"  [green]✓[/green] {env_var}\n\n"
            "[bold]Next:[/bold]\n"
            "  [dim]1.[/dim] Restart Claude Code  [dim](/exit, then `claude`)[/dim]\n"
            "  [dim]2.[/dim] Ask naturally — the skill will use the new key",
            border_style="green", padding=(1, 2)))
        return 0

    # ---- Service info panel ----
    lines = [
        f"[bold]{entry.get('name', service)}[/bold]  [dim]— {entry.get('description', '')}[/dim]",
        "",
        f"  Get key:   [magenta]{signup_url}[/magenta]",
    ]
    if key_example:
        lines.append(f"  Format:    [dim]{key_example}[/dim]")
    if friction_note:
        lines.append(f"  Friction:  [dim]{friction_note}[/dim]")
    lines.append(f"  Env var:   [cyan]{env_var}[/cyan]" + (" [dim](+ others, multi-step)[/dim]" if multi_var else ""))
    console.print()
    console.print(Panel.fit("\n".join(lines), border_style="cyan"))
    console.print()

    # ---- Offer to open browser ----
    if not args.no_browser and sys.stdin.isatty():
        if questionary.confirm(
            f"Open {signup_url} in your browser now?",
            default=True,
            style=QS_STYLE,
        ).ask():
            try:
                webbrowser.open(signup_url)
                console.print("[dim]  (browser opened)[/dim]")
            except Exception as e:
                console.print(f"[dim]  (couldn't open browser: {e})[/dim]")
        console.print()

    # ---- Collect key(s) ----
    # Special case: jira needs 3 inputs (email + base URL + token)
    settings = load_json(SETTINGS_LOCAL)
    env_block = settings.setdefault("env", {})
    to_save = {}  # env_var -> value

    if service == "jira":
        console.print("[dim]Jira needs 3 values:[/dim]")
        base = questionary.text(
            "JIRA_BASE_URL:",
            instruction="(e.g. https://yourcompany.atlassian.net)",
            style=QS_STYLE,
        ).ask()
        if not base:
            return 130
        email = questionary.text("JIRA_EMAIL:", style=QS_STYLE).ask()
        if not email:
            return 130
        token = questionary.password(
            "JIRA_API_TOKEN:",
            style=QS_STYLE,
        ).ask()
        if not (base and email and token):
            console.print("[red]error:[/red] all three values required")
            return 1
        to_save = {"JIRA_BASE_URL": base.strip(), "JIRA_EMAIL": email.strip(), "JIRA_API_TOKEN": token}
    else:
        if args.from_stdin:
            value = sys.stdin.read().strip()
        elif args.from_file:
            value = Path(args.from_file).read_text().strip()
        else:
            value = questionary.password(
                f"Paste your {env_var}:",
                style=QS_STYLE,
            ).ask()
            if value is None:  # Ctrl+C
                return 130
        if not value:
            console.print("[red]error:[/red] empty input")
            return 1
        # Validate format if we have a regex
        if regex_str and not re.match(regex_str, value):
            console.print(f"[yellow]warning:[/yellow] doesn't match expected format ({key_example})")
            if sys.stdin.isatty():
                if not questionary.confirm("Save anyway?", default=False, style=QS_STYLE).ask():
                    console.print("[dim]Cancelled.[/dim]")
                    return 1
        to_save = {env_var: value}

    # ---- Idempotency check ----
    all_same = all(env_block.get(k) == v for k, v in to_save.items())
    if all_same:
        console.print()
        console.print(f"[dim]· All credentials for {service} already set with the same value. No changes.[/dim]")
        return 0

    # ---- Backup + write ----
    bak = backup_file(SETTINGS_LOCAL)
    if bak:
        console.print(f"[dim]Backup: {bak}[/dim]")

    for k, v in to_save.items():
        env_block[k] = v

    SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_LOCAL, "w") as f:
        json.dump(settings, f, indent=2)

    # ---- Success panel ----
    console.print()
    success_lines = [
        f"[green bold]✓ {service} credentials saved.[/green bold]",
        "",
    ]
    for k in to_save:
        success_lines.append(f"  [green]✓[/green] {k}")
    success_lines.append("")
    success_lines.append("[bold]Next:[/bold]")
    success_lines.append("  [dim]1.[/dim] Restart Claude Code  [dim](close & reopen, or run `/exit` then `claude`)[/dim]")
    success_lines.append("  [dim]2.[/dim] Retry your original request — the skill should now work")
    success_lines.append("")
    success_lines.append(f"[dim]Verify: [magenta]teleport-setup --scan[/magenta][/dim]")

    console.print(Panel.fit("\n".join(success_lines), border_style="green", padding=(1, 2)))
    return 0


def ensure_claude_code_installed() -> bool:
    """Check that Claude Code is set up (config file exists). Returns True if OK, False after printing guidance."""
    if not CLAUDE_CONFIG.exists():
        console.print()
        console.print(Panel.fit(
            "[yellow]Claude Code config not found at ~/.claude.json[/yellow]\n\n"
            "[dim]teleport-setup works with installed Claude Code MCPs.[/dim]\n"
            "[dim]If Claude Code isn't installed yet, see:[/dim]\n"
            "  [magenta]https://code.claude.com/[/magenta]\n\n"
            "[dim]If it IS installed, run `claude` once to initialize the config,\nthen come back.[/dim]",
            title="teleport",
            border_style="yellow",
        ))
        return False
    return True


def cmd_scan(args: argparse.Namespace) -> int:
    if not ensure_claude_code_installed():
        return 1
    knowledge = load_knowledge(args.knowledge)
    config = load_json(CLAUDE_CONFIG)
    settings = load_json(SETTINGS_LOCAL)
    existing_env = settings.get("env", {})
    disabled_map = get_disabled_mcps(config)

    mcps = detect_mcps(config)
    plan = build_plan(mcps, knowledge, existing_env, disabled_map)

    print_header()

    if not plan:
        console.print("  [dim]No MCPs installed — nothing to migrate.[/dim]")
        console.print()
        console.print("  [dim]You can still use teleport skills directly. Add a credential with:[/dim]")
        console.print("    [magenta]teleport-setup add-key <service>[/magenta]")
        console.print("  [dim]then ask Claude Code for something that service covers.[/dim]")
        console.print()
        return 0

    print_summary(plan)
    print_list(plan)
    return 0


def cmd_interactive(args: argparse.Namespace) -> int:
    """Radically simple flow: auto-migrate everything ready (zero risk — only disabled, reversible),
    then walk through setup for anything that needs credentials, then final summary."""
    if not ensure_claude_code_installed():
        return 1

    telemetry_ping_once("/first-run", TELEMETRY_MARKER)

    knowledge = load_knowledge(args.knowledge)
    config = load_json(CLAUDE_CONFIG)
    settings = load_json(SETTINGS_LOCAL)
    existing_env = settings.get("env", {})
    disabled_map = get_disabled_mcps(config)

    mcps = detect_mcps(config)
    plan = build_plan(mcps, knowledge, existing_env, disabled_map)

    # ── Header ────────────────────────────────────
    console.print()
    console.print("  [bold]teleport[/bold]")
    console.print("  [dim]migrate your Claude Code MCPs[/dim]")
    console.print()

    if not plan:
        console.print("  [dim]No MCPs installed — nothing to migrate.[/dim]")
        console.print()
        console.print("  [dim]You can still use teleport skills directly. Add a credential with:[/dim]")
        console.print("    [magenta]teleport-setup add-key <service>[/magenta]")
        console.print("  [dim]then ask Claude Code for something that service covers.[/dim]")
        console.print()
        return 0

    ready = [p for p in plan if p["status"] == "ready"]
    setup_items = [p for p in plan if p["status"] == "needs-setup"]
    done = [p for p in plan if p["status"] == "already-migrated"]
    unsup = [p for p in plan if p["status"] == "unsupported"]

    if args.mcp:
        ready = [p for p in ready if p["name"] == args.mcp]
        setup_items = [p for p in setup_items if p["name"] == args.mcp]

    found_names = [p["name"] for p in plan]
    console.print(f"  [dim]Found:[/dim] {', '.join(found_names)}")
    console.print()

    if not ready and not setup_items:
        for item in done:
            console.print(f"  [dim]·[/dim] [dim]{item['name']} — already on teleport[/dim]")
        for item in unsup:
            console.print(f"  [dim]·[/dim] [dim]{item['name']} — {item.get('label', 'not supported')}[/dim]")
        console.print()
        console.print("  [dim]Nothing to do.[/dim]")
        console.print()
        return 0

    if args.dry_run:
        console.print(f"  [yellow](dry-run)[/yellow] would migrate: {', '.join(p['name'] for p in ready) or '(none)'}")
        console.print(f"  [yellow](dry-run)[/yellow] would walk setup: {', '.join(p['name'] for p in setup_items) or '(none)'}")
        console.print()
        return 0

    # ── PHASE 1: auto-migrate + disable ready items ──
    migrated = []
    bak_sl = backup_file(SETTINGS_LOCAL) if ready else None
    bak_cc = backup_file(CLAUDE_CONFIG) if ready else None
    env_block = settings.setdefault("env", {})

    if ready:
        for item in ready:
            env_block[item["env_var"]] = item["cred_value"]
            disable_mcp_in_config(config, item["scope"], item["name"])
            migrated.append(item)
            console.print(f"  [green]✓[/green] {item['name']}  [dim]migrated + disabled MCP[/dim]")
        with open(SETTINGS_LOCAL, "w") as f:
            json.dump(settings, f, indent=2)
        with open(CLAUDE_CONFIG, "w") as f:
            json.dump(config, f, indent=2)
        telemetry_ping("/migration")

    # Show skipped (already-migrated + unsupported) inline for completeness
    for item in done:
        console.print(f"  [dim]·[/dim] [dim]{item['name']}  already on teleport (skipped)[/dim]")
    for item in unsup:
        console.print(f"  [dim]·[/dim] [dim]{item['name']}  {item.get('label', 'not supported')} (skipped)[/dim]")

    if ready or done or unsup:
        console.print()

    # ── PHASE 2: walk through setup carousel ──
    setup_done = []
    setup_skipped = []

    if setup_items:
        # TTY guard — carousel needs interactive terminal
        if not sys.stdin.isatty():
            for item in setup_items:
                setup_skipped.append(item["name"])
                console.print(f"  [yellow]![/yellow] {item['name']}  [dim]needs setup — run `teleport-setup add-key {item['mcp_id']}` in a terminal[/dim]")
            console.print()
        else:
            word = f"{len(setup_items)} that need{'s' if len(setup_items) == 1 else ''} credentials"
            console.print(f"  [bold]Now let's set up {word}:[/bold]")
            console.print()

            quit_all = False
            for i, item in enumerate(setup_items, 1):
                if quit_all:
                    setup_skipped.append(item["name"])
                    continue
                service = item["mcp_id"]
                hint = item.get("setup_hint", "")
                console.print(f"  [bold][ {i}/{len(setup_items)} ] {item['name']}[/bold]  [dim]— {hint}[/dim]")

                action = questionary.select(
                    "",
                    choices=[
                        questionary.Choice("yes — walk me through it", value="yes"),
                        questionary.Choice("skip — I'll do it later", value="skip"),
                        questionary.Choice("quit — skip all remaining", value="quit"),
                    ],
                    style=QS_STYLE,
                ).ask()

                if action is None or action == "quit":
                    quit_all = True
                    setup_skipped.append(item["name"])
                    console.print(f"  [dim]· skipped[/dim]")
                    console.print()
                    continue
                if action == "skip":
                    setup_skipped.append(item["name"])
                    console.print(f"  [dim]· skipped — run `teleport-setup add-key {service}` when ready[/dim]")
                    console.print()
                    continue

                fake_args = argparse.Namespace(
                    service=service, no_browser=False, from_stdin=False, from_file=None,
                    knowledge=args.knowledge,
                )
                rc = cmd_add_key(fake_args)
                if rc == 0:
                    setup_done.append(item["name"])
                    # Also disable the MCP server config since credential is now in env
                    if disable_mcp_in_config(config, item["scope"], item["name"]):
                        with open(CLAUDE_CONFIG, "w") as f:
                            json.dump(config, f, indent=2)
                else:
                    setup_skipped.append(item["name"])
                console.print()

    # ── FINAL SUMMARY — framed panel ──
    all_migrated = [p["name"] for p in migrated] + setup_done
    lines = []
    lines.append("[green bold]✓ Done.[/green bold]")
    lines.append("")
    if all_migrated:
        lines.append("[bold]Migrated + disabled:[/bold]")
        for name in all_migrated:
            lines.append(f"  [green]✓[/green] {name}")
    if setup_skipped:
        if all_migrated:
            lines.append("")
        lines.append("[bold]Skipped (need setup):[/bold]")
        for name in setup_skipped:
            lines.append(f"  [dim]○[/dim] [dim]{name}[/dim]")
        lines.append("[dim]Run `teleport-setup add-key <name>` when ready.[/dim]")
    lines.append("")
    lines.append("[dim]Your MCPs are disabled, not deleted.[/dim]")
    lines.append("[dim]Re-enable any time:[/dim]")
    lines.append("  [magenta]claude mcp enable <name>[/magenta]")
    lines.append("  [dim]— or ask your agent: \"re-enable the <name> MCP\"[/dim]")
    lines.append("")
    lines.append("1️⃣  Restart Claude Code  [dim](/exit, then `claude`)[/dim]")
    lines.append("2️⃣  Ask naturally — or say [bold]\"use teleport\"[/bold] if it doesn't activate")
    lines.append("")
    lines.append("[bold green]Happy coding![/bold green]")

    console.print()
    console.print(Panel.fit("\n".join(lines), border_style="green", padding=(1, 2)))
    console.print()
    return 0


HELP_EPILOG = """\
examples:
  teleport-setup                      interactive: scan, pick MCPs, migrate
  teleport-setup --scan               preview only (no prompts, no changes)
  teleport-setup --yes                migrate & remove everything ready, no prompts
  teleport-setup add-key              guide you to add an API key for any service
  teleport-setup add-key stripe       add-key for Stripe specifically
  teleport-setup --mcp notion         only process one specific MCP

common workflows:

  Setting up teleport for the first time:
  $ teleport-setup --scan             # see what's installed
  $ teleport-setup                    # migrate existing MCPs with creds
  # restart Claude Code

  Adding a credential for a new service (no MCP installed):
  $ teleport-setup add-key github     # guided: open browser, paste, validate, save
  # restart Claude Code

docs & issues:
  https://github.com/mnlt/teleport
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="teleport-setup",
        description=(
            "Migrate installed Claude Code MCPs to teleport — moves their credentials "
            "to env vars so skills can bypass the MCP via HTTP, and optionally removes "
            "the now-redundant MCP server configs."
        ),
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"teleport-setup {VERSION}")
    parser.add_argument("--scan", action="store_true",
                        help="read-only preview (no prompts, no changes)")
    parser.add_argument("--yes", "-y", "--no-input", dest="yes", action="store_true",
                        help="non-interactive: migrate & remove all ready MCPs")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="show what would be migrated without writing")
    parser.add_argument("--keep-servers", action="store_true",
                        help="migrate credentials but don't remove MCP server entries")
    parser.add_argument("--mcp", metavar="NAME",
                        help="only process a specific MCP by name")
    parser.add_argument("--knowledge", default=KNOWLEDGE_URL,
                        help=argparse.SUPPRESS)

    # Subcommands (optional — default is interactive migrate)
    sub = parser.add_subparsers(dest="subcommand")

    p_addkey = sub.add_parser("add-key",
                              help="add an API key for a service (guided flow with browser + validation)")
    p_addkey.add_argument("service", nargs="?", help="service name (e.g. github, stripe). Omit to pick interactively.")
    p_addkey.add_argument("--no-browser", action="store_true", help="don't offer to open the signup URL in browser")
    p_addkey.add_argument("--from-stdin", action="store_true", help="read key from stdin instead of prompting")
    p_addkey.add_argument("--from-file", metavar="PATH", help="read key from a file instead of prompting")

    args = parser.parse_args()
    try:
        if args.subcommand == "add-key":
            return cmd_add_key(args)
        if args.scan:
            return cmd_scan(args)
        return cmd_interactive(args)
    except KeyboardInterrupt:
        console.print("\n[dim]interrupted[/dim]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
