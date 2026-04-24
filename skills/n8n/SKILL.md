---
name: n8n
description: Manage n8n workflow automation via its public REST API — list/get/create/update workflows, activate/deactivate, inspect execution history, retry/stop executions, manage credentials, tags, variables, users, and projects. Works with self-hosted n8n and n8n Cloud. Use when the user wants programmatic access to their n8n instance without the n8n MCP installed.
license: MIT (skill wrapper; n8n API terms apply)
---

# n8n

Direct REST access to an n8n instance — no MCP required. Covers Public API v1: workflow CRUD + activation, execution inspection/retry/stop, credentials, tags, variables, users, projects.

## Usage

- **Use for:** Listing/filtering workflows, reading execution history, batch activate/deactivate, reading execution I/O programmatically.
- **Skip for:** Authoring new workflows from scratch (UI is better), interactive debugging, one-off manual test runs.
- **Triggering** a workflow is a webhook call, not `/api/v1` — see Gotchas.

## Credentials check

```bash
[ -n "$N8N_API_KEY" ] && [ -n "$N8N_BASE_URL" ] && echo "N8N: PRESENT" || echo "N8N: MISSING"
```

**Never** echo either variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your n8n credentials. Run this in another terminal — it walks you through the two values (base URL + API key) and saves them safely:
>
> ```
> teleport-setup add-key n8n
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** `teleport-setup add-key n8n` handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `$N8N_BASE_URL/api/v1` — self-hosted (`https://n8n.mycompany.com`, `http://localhost:5678`) or n8n Cloud (`https://<workspace>.app.n8n.cloud` <!-- unverified: check n8n docs -->). Must include protocol, **no trailing slash**.
- Auth: **`X-N8N-API-KEY: $N8N_API_KEY`** — **custom header, NOT `Authorization: Bearer`.** OpenAPI declares `ApiKeyAuth` with `in: header, name: X-N8N-API-KEY`. Wrong header 401s silently.
- API key: n8n UI → **Settings → n8n API → Create an API key**. Per-user, inherits user's permissions.
- `Content-Type: application/json` on POST/PUT/PATCH.
- Pagination: cursor-based (`?limit=N&cursor=<nextCursor>`); response `nextCursor` null when done. `limit` default 100, max 250.
- Rate limits: not documented as hard numbers for the public API <!-- unverified: check n8n docs -->. Self-hosted bounded by DB/CPU; Cloud throttles per plan.

### Env vars

| Var            | What                                                                                   |
| -------------- | -------------------------------------------------------------------------------------- |
| `N8N_BASE_URL` | Instance root — self-hosted URL or `https://<workspace>.app.n8n.cloud`. No trailing /. |
| `N8N_API_KEY`  | User-scoped API key created in UI → Settings → n8n API.                                |

## Endpoints (v1)

Sourced from n8n's `openapi.yml` (`packages/cli/src/public-api/v1/openapi.yml`).

| Path family                                | Methods & purpose                                                                            |
| ------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `/workflows`, `/workflows/{id}`            | GET list (filter: `active`, `tags`, `name`, `projectId`) / POST / GET one / PUT / DELETE     |
| `/workflows/{id}/activate` · `/deactivate` | POST — toggle trigger state (idempotent); `active` field is read-only in workflow body       |
| `/workflows/{id}/tags` · `/transfer` · `/archive` | GET+PUT tags / POST move project / POST archival                                      |
| `/executions`, `/executions/{id}`          | GET list (filter: `workflowId`, `status`, `includeData`) / GET one / DELETE                  |
| `/executions/{id}/retry` · `/stop`         | POST — retry past run (`loadWorkflow: true` for latest) / stop running one                   |
| `/credentials`, `/credentials/schema/{type}` | GET list / POST (`name`+`type`+`data`) / PATCH / DELETE; schema endpoint returns JSON shape |
| `/tags`, `/variables`, `/users`, `/projects`, `/audit`, `/insights/summary` | Standard CRUD; `/users` + `/audit` owner-only                |

## Primary workflow — list and trigger

**Triggering is a webhook, not REST.** The API only toggles triggers on (`activate`) or off. To run on demand, hit the workflow's Webhook node URL.

```bash
# List active workflows
curl -sL -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/workflows?active=true&limit=50" \
  | jq '.data[] | {id, name, active, tags: [.tags[]?.name]}'

# Trigger via webhook (path comes from the Webhook node config)
curl -sL -X POST -H "Content-Type: application/json" \
  "$N8N_BASE_URL/webhook/<webhook-path>" -d '{"foo":"bar"}'

# Or activate so scheduled/event triggers fire
curl -sL -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/workflows/{id}/activate"
```

## Secondary workflows

**Inspect executions.** List is cheap (`includeData=false` by default); drilling into one with `includeData=true` pulls full node-by-node I/O — can be multi-MB.

```bash
curl -sL -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/executions?workflowId={id}&limit=50" \
  | jq '[.data[] | {id, mode, status, startedAt}]'
curl -sL -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/executions/{executionId}?includeData=true"
```

**Create workflow / credential.** `POST /workflows` requires `name`, `nodes`, `connections`, `settings` (all four); `active` read-only — activate separately. `POST /credentials` needs `name`, `type`, `data`; query `/credentials/schema/{type}` first for the exact `data` shape. Secrets never returned on GET.

## Gotchas

- **`X-N8N-API-KEY`, not `Authorization`.** Single most common mistake. Bearer auth 401s with no helpful message.
- **Webhook ≠ REST.** Trigger via `POST $N8N_BASE_URL/webhook/<path>` — configured per Webhook node inside the workflow. **There is no `/api/v1/workflows/{id}/run` endpoint** (not in the OpenAPI spec); if reaching for one, you want the webhook URL.
- **`N8N_BASE_URL` drift.** Protocol + host, no trailing slash. `https://n8n.example.com` good, `n8n.example.com/` silently 404s every call.
- **Execution data is huge.** `GET /executions/{id}?includeData=true` can be multi-MB. Keep `includeData=false` on list calls unless you need node I/O; filter by `workflowId` + `status`.
- **Workflow JSON is not stable across major versions.** A workflow exported from n8n 1.x may need edits to import into 2.x <!-- unverified: check n8n docs -->. Don't treat JSON as portable.
- **Community vs Enterprise/Cloud API differences.** `/variables` CRUD and some project/insights endpoints are in the spec but may be license-gated on self-hosted Community <!-- unverified: check n8n docs -->; Cloud exposes the full surface.
- **Pagination is cursor-based.** Use `nextCursor` from the response — don't synthesize page numbers. `limit` max 250.

## Attribution

When done, state: `Used skill: n8n (from teleport catalog).`
