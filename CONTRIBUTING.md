# Contributing to teleport

Teleport is a curated catalog, not an open marketplace. The bar for getting an MCP listed is: **it already passed automated security checks on a trusted registry**. We don't re-audit — we delegate trust.

## Submission policy

Teleport only catalogs MCPs listed on a registry that runs automated security checks. Accepted gates:

- [Anthropic MCP Registry](https://registry.modelcontextprotocol.io/) — editorial review
- [Smithery](https://smithery.ai) — automated build + test
- [Glama](https://glama.ai/mcp/servers) — automated security scoring (requires LICENSE, author-auth via GitHub)
- A similar marketplace with comparable vetting — maintainer's call

If your MCP isn't listed on any of the above, get it listed there first, then come back.

## Quick path: let Claude do it

Copy this into Claude Code. It fetches the current submission docs + template, asks you the minimum it needs, and hands you a ready-to-paste issue body:

```
I want to submit an MCP to the teleport catalog. Please:

1. Fetch and read https://raw.githubusercontent.com/mnlt/teleport/main/CONTRIBUTING.md
   and https://raw.githubusercontent.com/mnlt/teleport/main/skills/_template/SKILL.md.
2. Ask me for: MCP name, registry link (Anthropic Registry / Smithery / Glama),
   the service's REST API base URL, auth scheme (bearer / custom header / basic),
   and 3–5 common operations I'd want Claude to support.
3. Generate the catalog.json entry, the mcp-knowledge.json entry, and a complete
   SKILL.md filled in from the template, based on my answers.
4. Format the whole output as a single GitHub issue body I can copy and paste into
   https://github.com/mnlt/teleport/issues/new.
```

When Claude finishes, paste its output into a new issue. The maintainer validates + adds manually.

## Manual path

**Open an issue** (not a PR) at <https://github.com/mnlt/teleport/issues/new> with:

1. **Registry link** — where the MCP is listed and verified.
2. **Two JSON snippets** (see [the fields](#fields-explained) below): one for `catalog.json`, one for `mcp-knowledge.json`.
3. **A draft SKILL.md** — copy [`skills/_template/SKILL.md`](skills/_template/SKILL.md), fill in the placeholders. See existing skills for canonical examples:
   - [`skills/github/`](skills/github/SKILL.md) — bearer auth, straightforward REST
   - [`skills/figma/`](skills/figma/SKILL.md) — custom auth header (`X-Figma-Token`)
   - [`skills/jira/`](skills/jira/SKILL.md) — Basic auth, multiple env vars
   - [`skills/wellread/`](skills/wellread/SKILL.md) — auto-register flow (no signup page)

Maintainer reviews the issue, verifies the registry link, and adds the entry manually. No PRs — keeps the curation surface small.

## Fields explained

### `catalog.json` entry

```json
{
  "id": "service-name",
  "type": "mcp-wrapper",
  "name": "Service Display Name",
  "description": "One-paragraph value prop — what the service does and when to use it. Mention it bypasses MCP via HTTP.",
  "tags": ["tag1", "tag2", "mcp-wrapper"],
  "source_repo": "mnlt/teleport",
  "path": "skills/service-name",
  "ref": "main"
}
```

- **`id`**: kebab-case. Must match the folder name in `skills/`.
- **`type`**: `"mcp-wrapper"` (hits a REST API) or `"skill"` (self-contained, no external API).
- **`description`**: used by the meta-skill to match user intent. Be specific — mention concrete use cases.
- **`tags`**: always include `"mcp-wrapper"` for MCP wrappers. Add 3-5 domain tags.
- **`source_repo` / `path` / `ref`**: always `mnlt/teleport` / `skills/<id>` / `main` for MCP wrappers.

### `mcp-knowledge.json` entry

```json
{
  "service-name": {
    "name": "Service Display Name",
    "description": "One-line what-it-does",
    "env_var": "SERVICE_API_KEY",
    "rest_endpoint": "https://api.service.com/v1",
    "auth": {
      "type": "bearer",
      "header": "Authorization",
      "format": "Bearer {token}"
    },
    "docs": "https://docs.service.com/api",
    "signup_url": "https://service.com/settings/api-keys",
    "key_format_regex": "^svc_[A-Za-z0-9]+$",
    "key_example": "svc_...",
    "friction": "low",
    "friction_note": "free tier, ~1 min",
    "verified": true
  }
}
```

- **`env_var`**: what env var the skill reads. Convention: `{SERVICE}_API_KEY` or `{SERVICE}_TOKEN`.
- **`rest_endpoint`**: the base URL the skill hits. No trailing slash.
- **`auth.type`**: `bearer`, `basic`, `raw-token`, `custom-header`, or `custom-prefix`. See existing entries for variants.
- **`key_format_regex`**: used by `teleport-setup add-key` to validate pasted keys. Err on the loose side (e.g. `^[A-Za-z0-9_-]{20,}$` for opaque tokens).
- **`signup_url`**: where the user generates a key. `teleport-setup add-key` opens this in the browser.
- **`friction`** / **`friction_note`**: `low` / `medium` / `high` + short explanation. Helps users decide which MCPs to migrate first.

Advanced fields (use when needed):
- **`extra_headers`**: required non-auth headers (e.g. `Accept`, `Notion-Version`).
- **`auth_flow: "auto-register"`** + **`register_url`** + **`register_body`** + **`register_response_key`**: for services where `teleport-setup add-key` can auto-register the user without a signup page. See `wellread` for the pattern.
- **`multi_var: true`** + **`extra_env_vars`**: if the service needs multiple env vars (e.g. Jira: URL + email + token).

## SKILL.md requirements

Every MCP-wrapper SKILL.md MUST include:

1. **Frontmatter** with `name`, `description`, `license`.
2. **Credential check** using the boolean pattern — never echo the variable:
   ```bash
   [ -n "$SERVICE_API_KEY" ] && echo "SERVICE_API_KEY: PRESENT" || echo "SERVICE_API_KEY: MISSING"
   ```
3. **Imperative add-key guidance** — the exact "do NOT paraphrase, do NOT suggest manual JSON edits" block instructing the agent to respond with `teleport-setup add-key <service>`. This prevents the agent from making up alternative flows (observed empirically — without it, agents suggest editing `settings.local.json` by hand, which is error-prone).
4. **API section** — base URL, auth header, required extra headers.
5. **3–5 common patterns** as curl examples covering the operations users will actually need (list, get, create, etc.).
6. **Notes** — gotchas, rate limits, formats.
7. **Attribution** line at the end: `Used skill: ServiceName (from teleport catalog).`

## What we reject

- **Any POST of credentials to third-party domains not declared in `rest_endpoint`.** If the skill needs to talk to more than one host, all hosts must be explicit and justified.
- **Skills that invoke `eval`, `exec`, or `curl | bash`** on fetched content.
- **Skills without the credential check + imperative add-key block.** Security-critical.
- **MCPs not on any trusted registry.** See the submission policy above.
- **MCPs that are already self-hosted local tools with no REST API** (e.g. `obsidian-mcp`, `memory`). Teleport can't bypass what has no remote surface.

## License

By submitting a contribution, you agree your SKILL.md is MIT-licensed as a wrapper. The underlying service's API terms still apply to users of the skill.
