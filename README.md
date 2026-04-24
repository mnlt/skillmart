# Teleport

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Skills in catalog](https://img.shields.io/badge/catalog-45%20entries-green.svg)](catalog.json) 
[![GitHub stars](https://img.shields.io/github/stars/mnlt/teleport?style=social)](https://github.com/mnlt/teleport/stargazers) 

**MCP, but without the MCP.**

Teleport replaces your MCPs with curated ephemeral skills that call the REST APIs directly (GitHub, Stripe, Notion…) with credentials in env vars, each loaded on demand — so you avoid having every MCP's schemas injected into context from the first message whether you use them or not.

## So what?

MCP is like having all your apps open at the same time. So you’ve already burned tokens before the first prompt. 

Teleport is like opening only the app you need, exactly when you need it - so you only spend tokens when it actually matters.

Context7, Superpowers, GitHub, Stripe? none of them loaded until you actually need them.

The result: a smaller baseline context per turn and an agent that composes calls instead of blindly consuming whatever an MCP tool returns.

> **Want teleport to support an MCP?** Thumbs-up (or add it) on the [MCP Request Board](https://github.com/mnlt/teleport/issues/1).
>
> **Want to submit your own MCP?** Increase adoption - users discover and use it while coding. See [CONTRIBUTING.md](CONTRIBUTING.md).

## What you save

MCP tool definitions get loaded into every turn. In a multi-server setup, that's tens of thousands of tokens paid upfront - every turn, for schemas the agent may not use. Bigger context windows raise the ceiling, but they don't change the per-turn cost, cache invalidation, or the "process everything the tool returns" problem.

Teleport skills don't pre-load. Nothing enters context from message one — no tool definitions, no schemas, no compounding across turns. A skill loads once, on demand, only when the agent actually needs it.

## Why not just…

**…reuse MCP since it already standardizes integration?** MCP solves "one integration, many clients". Teleport solves "keep the baseline context small when I'm only using one or two services per turn". Different problems. If you don't feel the per-turn baseline cost, MCP is fine.

**…lazy-load MCPs instead?** Claude Code's tool-search MCP does that. Teleport goes a step further — the MCP server is off entirely, loaded only when the skill fires.

**…handle OAuth like MCP does?** For API-key auth it's just an env var. For OAuth-based MCPs (Notion HTTP, Figma hosted, Atlassian Rovo) there's no OAuth bypass - the user generates a PAT from the service dashboard and teleport stores that. MCP's OAuth handling is genuinely nicer there.

## 1. Install

```bash
curl -sL https://raw.githubusercontent.com/mnlt/teleport/main/setup/install.sh -o /tmp/teleport-install.sh && bash /tmp/teleport-install.sh
```

Installs the `teleport-setup` CLI into `~/.local/bin` and the `teleport` meta-skill into `~/.claude/skills/teleport/`.

## 2. Setup

```bash
teleport-setup
```

Scans your installed MCPs, auto-migrates the ones whose credentials are already in the MCP's env block (copies them to `~/.claude/settings.local.json` and adds the MCP to `disabledMcpServers[]`), and walks you through the rest. Then restart Claude Code (`/exit`, then `claude`) and ask naturally - the agent calls the service's REST API directly via the matching skill.

Need a credential later?

```bash
teleport-setup add-key <service>
```

Opens the signup page, validates the format, saves it with masked input.

## 3. Use

Teleport can activate on its own, but if you want to be sure, drop "use teleport" in your prompt

```bash
How do I set up Next.js 15 app with Auth.js ... use teleport
```

## Two paths, depending on how the MCP was installed

Not every MCP stores its credential somewhere teleport can read. Both paths end up the same place: env var in `settings.local.json`, MCP disabled, skill hits REST API directly.

| Path | When it applies | What teleport does | User effort |
|------|-----------------|--------------------|-------------|
| **One-click migration** | Credential already in the MCP's `env` block in `~/.claude.json` - most self-hosted stdio MCPs (GitHub, Slack, Stripe, Supabase, Linear, etc. installed with `--env`) | Copies the credential to `settings.local.json`, disables the MCP | Zero typing |
| **Generate-and-paste** | Hosted / OAuth-based MCPs (Notion HTTP, Figma hosted, Atlassian Rovo) where the token lives in a Claude Code cache teleport can't access | Opens the signup page, you generate an API token, paste it (masked input) | One extra step, handled inline |

## Supported MCPs

Context7 · GitHub · Slack · Notion · Linear · Figma · Jira · Exa · Stripe · Supabase · Vercel · Netlify · Cloudflare · Railway · Resend · Sentry · PostHog · Lemon Squeezy · Discord · Wellread · n8n

## How migration works

1. Read `~/.claude.json` → find installed MCPs and any credentials in their `env` blocks.
2. For each MCP matched in `mcp-knowledge.json`, copy the credential to `~/.claude/settings.local.json` under `env`.
3. Add the MCP name to `disabledMcpServers[]` in the same config - the server stops loading, its tool schemas disappear from the agent's context.
4. When you ask for something that service covers, the agent loads the matching skill from the teleport catalog, reads the env var, and hits the REST API.

Reversible at any time:

```bash
claude mcp enable <name>
```

## Skills (secondary)

Teleport also ships self-contained skills:

- **10 from [`anthropics/skills`](https://github.com/anthropics/skills)** - pdf, docx, xlsx, pptx, canvas-design, webapp-testing, mcp-builder, frontend-design, algorithmic-art, slack-gif-creator.

All fetched on-demand from `/tmp/` when you ask for something they cover; nothing persists in `~/.claude/skills/`.

## Catalog

See [catalog.json](./catalog.json) - 45 entries (21 MCP-wrappers + 24 self-contained skills. Each skill's license is governed by its upstream `source_repo`.

## Design notes

- **Disable, don't delete:** `disabledMcpServers[]` keeps the config intact - enable any server again with one command.
- **Credentials never echo:** the credential check uses `[ -n "$VAR" ] && echo PRESENT || echo MISSING` so values never leak to the transcript.
- **Imperative skill guidance:** when a credential is missing, the skill instructs the agent to respond with a specific `teleport-setup add-key <service>` message verbatim - no paraphrasing, no suggestions to hand-edit `settings.local.json`.
- **No runtime deps beyond `curl`, Python 3.10+, and Claude Code.**

## Caveats

- **Claude Code only.** Leans on Claude (Sonnet/Opus) knowing the popular REST APIs. Smaller or weaker models - local LLMs, other cloud providers - won't work the same way. For obscure APIs the skill contains the curl recipe so the model's prior knowledge matters less; but the baseline assumption is Claude Code + Sonnet or Opus.
- Self-contained skills that need Python packages, browsers, or system tools still require those installed locally.
