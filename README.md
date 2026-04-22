# Teleport

Ephemeral MCP migration for Claude Code. Move credentials to env vars, disable the MCP servers (reversible), and let the agent hit the REST APIs directly — smaller baseline context per turn, and the agent composes calls instead of swallowing whatever the MCP tool returns.

## What you save

MCP tool definitions get loaded into every turn. In a multi-server setup, that's tens of thousands of tokens paid upfront — every turn, for schemas the agent may not use. Bigger context windows raise the ceiling, but they don't change the per-turn cost, cache invalidation, or the "process everything the tool returns" problem.

Measured via Anthropic's `count_tokens` endpoint (real Claude tokenizer), 2026-04-22:

| MCP        | Tools | Tokens |
|------------|------:|-------:|
| Notion     | 22    | 22,056 |
| Linear     | 42    |  5,920 |
| GitHub     | 26    |  5,385 |
| Figma      |  2    |  1,591 |
| Slack      |  8    |  1,411 |

Community-reported (from public `/context` dumps):

| MCP        | Tokens |
|------------|-------:|
| Asana      | ~30,000 |
| Google Docs | ~25,000 |
| Google Calendar | ~15,000 |
| Atlassian (Jira) | ~12,000 |
| Gmail      |  ~8,000 |

Teleport-loaded skills cost ~400–800 tokens each, only when the agent needs them.

**Reproduce**: `ANTHROPIC_API_KEY=… python3 setup/measure_tokens.py`. Counts drift with each MCP version — run `/context` in Claude Code for your actual numbers.

## Why not just…

**…reuse MCP since it already standardizes integration?** MCP solves "one integration, many clients". Teleport solves "keep the baseline context small when I'm only using one or two services per turn". Different problems. If you don't feel the per-turn baseline cost, MCP is fine.

**…lazy-load MCPs instead?** Claude Code's tool-search MCP does that. Teleport goes a step further — the MCP server is off entirely, loaded only when the skill fires.

**…handle OAuth like MCP does?** For API-key auth it's just an env var. For OAuth-based MCPs (Notion HTTP, Figma hosted, Atlassian Rovo) there's no OAuth bypass — the user generates a PAT from the service dashboard and teleport stores that. MCP's OAuth handling is genuinely nicer there.

## Install

```bash
curl -sL https://raw.githubusercontent.com/mnlt/teleport/main/setup/install.sh -o /tmp/teleport-install.sh && bash /tmp/teleport-install.sh
```

Installs the `teleport-setup` CLI into `~/.local/bin` and the `teleport` meta-skill into `~/.claude/skills/teleport/`.

## Use

```bash
teleport-setup
```

Scans your installed MCPs, auto-migrates the ones whose credentials are already in the MCP's env block (copies them to `~/.claude/settings.local.json` and adds the MCP to `disabledMcpServers[]`), and walks you through the rest. Then restart Claude Code (`/exit`, then `claude`) and ask naturally — the agent calls the service's REST API directly via the matching skill.

Need a credential later?

```bash
teleport-setup add-key <service>
```

Opens the signup page, validates the format, saves it with masked input.

## Two paths, depending on how the MCP was installed

Not every MCP stores its credential somewhere teleport can read. Both paths end up the same place: env var in `settings.local.json`, MCP disabled, skill hits REST API directly.

| Path | When it applies | What teleport does | User effort |
|------|-----------------|--------------------|-------------|
| **One-click migration** | Credential already in the MCP's `env` block in `~/.claude.json` — most self-hosted stdio MCPs (GitHub, Slack, Stripe, Supabase, Linear, etc. installed with `--env`) | Copies the credential to `settings.local.json`, disables the MCP | Zero typing |
| **Generate-and-paste** | Hosted / OAuth-based MCPs (Notion HTTP, Figma hosted, Atlassian Rovo) where the token lives in a Claude Code cache teleport can't access | Opens the signup page, you generate an API token, paste it (masked input) | One extra step, handled inline |

## Supported MCPs

20 MCP-wrapper skills — credential check, imperative "run `teleport-setup add-key`" guidance, and curl recipes for the common operations:

Context7 · GitHub · Slack · Notion · Linear · Figma · Jira · Exa · Stripe · Supabase · Vercel · Netlify · Cloudflare · Railway · Resend · Sentry · PostHog · Lemon Squeezy · Discord · Wellread

## How migration works

1. Read `~/.claude.json` → find installed MCPs and any credentials in their `env` blocks.
2. For each MCP matched in `mcp-knowledge.json`, copy the credential to `~/.claude/settings.local.json` under `env`.
3. Add the MCP name to `disabledMcpServers[]` in the same config — the server stops loading, its tool schemas disappear from the agent's context.
4. When you ask for something that service covers, the agent loads the matching skill from the teleport catalog, reads the env var, and hits the REST API.

Reversible at any time:

```bash
claude mcp enable <name>
```

## Skills (secondary)

Teleport also ships 10 self-contained skills from [`anthropics/skills`](https://github.com/anthropics/skills) — pdf, docx, xlsx, pptx, canvas-design, webapp-testing, mcp-builder, frontend-design, algorithmic-art, slack-gif-creator. These are fetched on-demand from `/tmp/` when you ask for something they cover; nothing persists in `~/.claude/skills/`.

## Catalog

See [catalog.json](./catalog.json) — 30 entries (20 MCP-wrappers + 10 self-contained skills). Each skill's license is governed by its upstream `source_repo`.

## Adding entries

Teleport only catalogs MCPs already listed on a trusted registry that runs automated security checks ([Anthropic MCP Registry](https://registry.modelcontextprotocol.io/), [Smithery](https://smithery.ai), [Glama](https://glama.ai/mcp/servers), or similar). We delegate security auditing to those registries — we don't re-audit.

**Want teleport to support an MCP you use?** Open a ["Request an MCP" issue](../../issues/new?template=request-mcp.yml), or thumbs-up the service on the pinned MCP Request Board. This is the path if you're a user, not the MCP author.

**Built an MCP and want it in the catalog?** See [CONTRIBUTING.md](CONTRIBUTING.md) — requires a draft SKILL.md and a registry link.

## Design notes

- **Disable, don't delete:** `disabledMcpServers[]` keeps the config intact — enable any server again with one command.
- **Credentials never echo:** the credential check uses `[ -n "$VAR" ] && echo PRESENT || echo MISSING` so values never leak to the transcript.
- **Imperative skill guidance:** when a credential is missing, the skill instructs the agent to respond with a specific `teleport-setup add-key <service>` message verbatim — no paraphrasing, no suggestions to hand-edit `settings.local.json`.
- **No runtime deps beyond `curl`, Python 3.10+, and Claude Code.**

## Telemetry

Teleport pings an anonymous event counter on three moments to know how many people actually use it:

- `install-completed` — when `install.sh` finishes successfully
- `first-run` — the first time you run `teleport-setup` on a machine
- `migration` — after a successful migration of at least one MCP

No IP stored, no PII, no correlation between pings. Counter runs on [goatcounter.com](https://www.goatcounter.com) (privacy-first). Dashboard: <https://teleport.goatcounter.com/>.

**Opt out**: set `TELEPORT_NO_TELEMETRY=1` in your environment before running the installer or the CLI.

## Caveats

- **Claude Code only.** Leans on Claude (Sonnet/Opus) knowing the popular REST APIs. Smaller or weaker models — local LLMs, other cloud providers — won't work the same way. For obscure APIs the skill contains the curl recipe so the model's prior knowledge matters less; but the baseline assumption is Claude Code + Sonnet or Opus.
- Token counts drift with each MCP version update. Re-run `setup/measure_tokens.py` or `/context` for current numbers.
- Self-contained skills that need Python packages, browsers, or system tools still require those installed locally.
