# teleport-setup

CLI tool to detect installed Claude Code MCPs and migrate their credentials to environment variables in `~/.claude/settings.local.json` — so skills from the teleport catalog can use them via HTTP bypass without the MCP server installed.

## Install

One-liner:

```bash
curl -sL https://raw.githubusercontent.com/mnlt/teleport/main/setup/teleport-setup.py -o /tmp/teleport-setup.py
```

Then run with `python3 /tmp/teleport-setup.py <command>`. Requires Python 3.8+ (standard library only, zero dependencies).

## Commands

```
teleport-setup scan                  # detect MCPs, print plan, no changes
teleport-setup migrate               # interactive migration of Category A MCPs
teleport-setup migrate --dry-run     # show plan without writing
teleport-setup migrate --yes         # non-interactive, migrate all Category A
teleport-setup migrate --mcp github  # only process one MCP
teleport-setup --version
```

## How it works

1. Loads `mcp-knowledge.json` from the teleport repo (or `--knowledge` path).
2. Scans `~/.claude.json` for installed MCP servers across all project scopes.
3. Classifies each MCP:
   - **Category A** (HTTP-rescuable): migratable — can bypass MCP via REST API with env var.
   - **Category B** (locally-rescuable): redundant — native Bash tools already cover it.
   - **Category C** (stdio-only, e.g. Playwright): cannot migrate — keep MCP installed.
   - **Unknown**: not in knowledge base, skipped.
4. For Category A with credentials found in MCP config, extracts the value and writes it to `settings.local.json` under `env`.
5. Idempotent: skips entries already migrated with the same value.

## Safety guarantees

- **Backups** made of `settings.local.json` before any write (suffix `.bak-<timestamp>`).
- **No secret values printed** to stdout — only PRESENT/MISSING booleans and var names.
- **Dry-run mode** shows the plan without writing.
- **Interactive confirmation** per MCP unless `--yes` is passed.
- **No MCP removal**: the tool does NOT call `claude mcp remove` — it only adds env vars. You decide when to uninstall MCPs manually after testing.

## After migration

```bash
# Restart your Claude Code session so it picks up the new env vars.
# Then either keep the MCPs installed (dual-track) or remove those you're
# confident the env bypass covers:
claude mcp remove <name>
```

## Limitations

- Only extracts credentials stored directly in the MCP's `env` block or common header patterns (`Authorization: Bearer ...`). OAuth tokens stored in vendor-specific caches (e.g. `ctx7 login`) cannot be migrated — the user must regenerate an API key.
- Does not handle MCPs not in `mcp-knowledge.json` — community MCPs require adding a knowledge entry first.
- Does not scan project-level `.mcp.json` files (only user-scope `~/.claude.json`). Planned for v0.2.

## Expanding the knowledge base

`mcp-knowledge.json` lives in the teleport repo root. Each entry has `env_var`, `rest_endpoint`, `auth` scheme, and optional `alt_env_vars`. Submit PRs adding new MCPs.
