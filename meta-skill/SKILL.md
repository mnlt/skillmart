---
name: teleport
description: Discover and execute specialized skills from a curated marketplace catalog on GitHub, fetched on-demand and run ephemerally (no permanent installation). The catalog covers a broad and growing range — document generation (PDF/Word/Excel/PowerPoint), visual design, presentations, web app testing, animated GIFs, dev tooling (MCP scaffolding, frontend components), creative outputs (algorithmic art), technical documentation lookup (library/API/framework references), and more. Consult this skill whenever the user asks for a capability that could plausibly be covered by a community skill — the catalog is the source of truth, not this description.
---

# Teleport — Ephemeral Skill Execution

## When to activate

Activate this skill whenever the user's request could plausibly be covered by a specialized community skill. Examples span document generation, visual design, dev tooling, testing, library/API documentation lookup, creative outputs, and more — see the "Example triggers" table below, but treat it as illustrative, not exhaustive.

**Always fetch the catalog before deciding this skill is not applicable.** The catalog grows and this description lags. Do not gatekeep based on the description alone — the protocol's Step 1 (fetch catalog) is the authoritative source of truth for what is and isn't available.

Only skip this skill for clearly native tasks with no plausible community-skill coverage: debugging the user's existing code, explaining concepts, editing local files without specialized output formats, searching the current codebase.

## Protocol

### Step 1 — Fetch the catalog

Use Bash:

```bash
curl -sL https://raw.githubusercontent.com/mnlt/teleport/main/catalog.json
```

Parse the output as JSON. Each entry in `skills[]` has: `id`, `name`, `description`, `tags`, `source_repo`, `path`, `ref`.

### Step 2 — Match user intent

Score each skill against the user's request using `description` and `tags`.

- **Single strong match** → proceed to step 3.
- **2+ plausible candidates** → briefly list the top 2-3 to the user and ask which.
- **No plausible match** → tell the user "no suitable skill found in the teleport catalog" and fall back to native capabilities.

### Step 3 — Fetch the matched skill's SKILL.md

Build the raw URL:
```
https://raw.githubusercontent.com/{source_repo}/{ref}/{path}/SKILL.md
```

Download it to a temp dir:

```bash
mkdir -p /tmp/teleport/{id}
curl -sL {url} -o /tmp/teleport/{id}/SKILL.md
```

Read the downloaded file with the Read tool. Inform the user: `Using skill: {name} (from {source_repo})`.

### Step 4 — Follow the skill, lazy-fetching auxiliary files

As you follow the SKILL.md instructions:

- **If instructions reference another filename** within the skill folder (e.g. "see REFERENCE.md", "read FORMS.md", "run scripts/extract.py"), construct its raw URL:
  ```
  https://raw.githubusercontent.com/{source_repo}/{ref}/{path}/{referenced-file}
  ```
  and download it to `/tmp/teleport/{id}/{referenced-file}` (preserving subdirectories with `mkdir -p`).
- **To execute a script**, run it from its cached temp path.
- **Recurse on demand**: if a fetched markdown itself references another file, fetch that too when its moment arrives — never all-at-once eagerly.
- If you're unsure whether a file exists in the upstream folder, try fetching it; a 404 is a cheap signal.

### Step 5 — Handle failures

- **Fetch fails (404, network)** → report the failing URL, then either fall back to native or ask user to install the skill normally.
- **Missing runtime dependency** (e.g. script needs Python packages not installed) → report the dependency, do NOT fake execution.
- **Ambiguous reference** (e.g. "see the templates folder" without filename) → ask the user for clarification, or list the upstream folder via `curl -sL https://api.github.com/repos/{source_repo}/contents/{path}?ref={ref}`.

### Step 6 — Do NOT persist by default

Never copy fetched files into `~/.claude/skills/` automatically. Everything lives in `/tmp/teleport/` and disappears with the session.

Only if the user explicitly says "install this permanently" or similar:
```bash
cp -r /tmp/teleport/{id}/ ~/.claude/skills/{id}/
```

## Attribution

When the task finishes, state briefly: `Used skill: {name} from {source_repo}.`

## Example triggers

| User says | Match |
|---|---|
| "Create a PDF from this data" | `pdf` |
| "Fill this PDF form" | `pdf` |
| "Read this .docx file" | `docx` |
| "Edit my Excel spreadsheet" | `xlsx` |
| "Build me a slide deck on X" | `pptx` |
| "Design a poster for Y" | `canvas-design` |
| "Test this webapp for accessibility" | `webapp-testing` |
| "Make an animated GIF for Slack saying Z" | `slack-gif-creator` |
| "Scaffold a new MCP server" | `mcp-builder` |
| "Build a React component for Q" | `frontend-design` |
| "Generate some algorithmic/generative art" | `algorithmic-art` |

## Notes

- Minimum 2 network round-trips (catalog + SKILL.md) before real work begins. Expect 1-2s latency.
- All skills in catalog v0.1.0 originate from `anthropics/skills`. Verify the upstream license before relying on any skill in production.
- Never upload user data to external services during fetch. Only GET requests to `raw.githubusercontent.com` and `api.github.com`.

## Credentials for fetched skills

If a fetched skill requires credentials (API keys, OAuth tokens, etc.) to authenticate with an external service or CLI, **look for them in the process environment variables** — do NOT expect them embedded in any SKILL.md file.

Naming convention to expect:
- `<SERVICE>_API_KEY` — generic API keys (e.g. `CONTEXT7_API_KEY`, `OPENAI_API_KEY`).
- `<SERVICE>_ACCESS_TOKEN` / `<SERVICE>_REFRESH_TOKEN` — OAuth tokens.
- `<SERVICE>_TOKEN` — generic token alias.

Check availability using a boolean pattern that **never echoes the value**:
```bash
[ -n "$CONTEXT7_API_KEY" ] && echo "CONTEXT7_API_KEY: PRESENT" || echo "CONTEXT7_API_KEY: MISSING"
```

**NEVER** use `echo "$VAR"` or `echo "${VAR:-MISSING}"` — the former echoes the actual token, the latter echoes the token when it's set. Both expose secrets to the conversation transcript. Use only the boolean pattern above.

If the required credential is missing (`MISSING`/empty), **stop and report** to the user which env var is expected — do not attempt to run the skill with partial auth, do not fall back to prompting the user for the token in chat, and do not silently proceed to an unauthenticated call that may fail opaquely. The user can add the missing variable to `~/.claude/settings.local.json` under the `env` block and restart the session.

Scope: only pass credentials to skills from a `source_repo` whose service identity matches the env var's `<SERVICE>` prefix (e.g. `CONTEXT7_*` → only to `upstash/context7` or explicit Context7-branded skills). Never forward tokens to unrelated third-party `source_repo`s.
