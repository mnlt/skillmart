---
name: vercel
description: Manage Vercel deployments, projects, environment variables, domains, DNS, and build/runtime logs via REST API. Use when the user wants to deploy, check a deploy status, rotate env vars, attach custom domains, or investigate failed builds without the Vercel MCP installed.
license: MIT (skill wrapper; Vercel API terms apply)
---

# Vercel

Operates Vercel via REST API — deployments, projects, env vars, domains/DNS, logs, teams, webhooks, Edge Config. Prefer over `vercel` CLI for scripted/team-scoped control.

## Usage

- **Use for:** Deploy status, triggering redeploys, rotating env vars, attaching domains, tailing build/runtime logs.
- **Skip for:** Framework/docs questions (use Context7), local build failures (`vercel dev`), editing `vercel.json` in a repo.

## Credentials check

```bash
[ -n "$VERCEL_TOKEN" ] && echo "VERCEL_TOKEN: PRESENT" || echo "VERCEL_TOKEN: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your vercel credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key vercel
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.vercel.com`
- Auth: `Authorization: Bearer $VERCEL_TOKEN`
- **`teamId` — #1 silent footgun.** Team-scoped tokens calling an endpoint without `?teamId=team_xxx` (or `slug=`) silently fall back to personal scope — wrong/empty results with 200 OK. `GET /v2/teams` once, cache, append everywhere.
- **Versioning is per-endpoint in the path** — list env vars is `v10`, update is `v9`, create project is `v11`, update project is `v9`. Guessing 404s; use the table.
- Pagination is **timestamp-based, not an opaque token.** `pagination.next` is a unix **millisecond** value; pass as `until=` (or `since=` to walk forward). Project list uses `from`.
- Rate limits per-endpoint; headers: `x-ratelimit-limit`, `x-ratelimit-remaining`, `x-ratelimit-reset` (unix sec). Notable: **runtime logs 100/min**, env create/update 120/min, env delete 60/min, domain create 120/hr, DNS create 100/hr.
- OpenAPI spec: `https://openapi.vercel.sh/` (single large JSON).

## Entity hierarchy

`team` (optional) → `project` (`prj_xxx`, owns env vars + domain attachments) → `deployment` (`dpl_xxx`, has `state` + `target`) → `event / log line`.

## Endpoints

| Group       | Method · Path                                                                               |
| ----------- | ------------------------------------------------------------------------------------------- |
| Deployments | `GET /v6/deployments` · `GET /v13/deployments/{idOrUrl}` · `POST /v13/deployments` · `DELETE /v13/deployments/{id}` |
| Deployments | `PATCH /v12/deployments/{id}/cancel` · `GET /v3/deployments/{idOrUrl}/events` (logs, `follow=1`) |
| Projects    | `GET /v10/projects` · `POST /v11/projects` · `GET · PATCH · DELETE /v9/projects/{idOrName}` |
| Env vars    | `GET · POST /v10/projects/{idOrName}/env` (POST supports `?upsert=true`)                    |
| Env vars    | `GET /v1/projects/{idOrName}/env/{id}` · `PATCH · DELETE /v9/projects/{idOrName}/env/{id}` · `DELETE /v1/projects/{idOrName}/env` (batch) |
| Domains     | `GET /v5/domains` · `POST /v7/domains` · `GET /v6/domains/{domain}/config` · `POST /v10/projects/{idOrName}/domains` |
| DNS         | `GET /v5/domains/{domain}/records` · `POST /v2/domains/{domain}/records` · `DELETE /v1/domains/records/{recordId}` |
| Teams       | `GET /v2/teams`                                                                             |
| Webhooks    | `GET · POST /v1/webhooks` · `GET · DELETE /v1/webhooks/{id}`                                |
| Edge Config | `GET · POST /v1/edge-config` · `GET · PATCH /v1/edge-config/{edgeConfigId}/items`           |
| Logs        | `GET /v1/projects/{projectId}/deployments/{deploymentId}/runtime-logs`                      |

## Primary workflows

**1. List recent deployments**

```bash
curl -sL -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v6/deployments?projectId=prj_xxx&limit=10&teamId=team_xxx" \
  | jq '.deployments[] | {uid, url, state, target, created, branch: .meta.githubCommitRef}'
```

**2. Set or rotate an env var**

Body: `key`, `value`, `type` (`encrypted` / `plain` / `sensitive` / `system`), `target` — **lowercase array** from `["production","preview","development"]`, optional `gitBranch`.

```bash
curl -sL -X POST -H "Authorization: Bearer $VERCEL_TOKEN" -H "Content-Type: application/json" \
  "https://api.vercel.com/v10/projects/prj_xxx/env?upsert=true&teamId=team_xxx" \
  -d '{"key":"DATABASE_URL","value":"postgres://…","type":"encrypted","target":["production"]}'
```

Env var changes **do not retroactively affect already-built deployments** — trigger a redeploy.

**3. Trigger a redeploy from a git source**

```bash
curl -sL -X POST -H "Authorization: Bearer $VERCEL_TOKEN" -H "Content-Type: application/json" \
  "https://api.vercel.com/v13/deployments?teamId=team_xxx&forceNew=1" \
  -d '{"name":"my-project","target":"production","gitSource":{"type":"github","repoId":123456789,"ref":"main"}}'
```

`gitSource.type` ∈ `github` / `github-limited` / `gitlab` / `bitbucket`. Set `target: "production"` explicitly — omitting yields a preview.

## Gotchas

- **`teamId` on team tokens.** Omitting silently falls back to your personal scope — wrong/empty results with 200 OK. Always pass `?teamId=team_xxx`.
- **Deployment state enum:** `BUILDING | ERROR | INITIALIZING | QUEUED | READY | CANCELED` (also `DELETED` in responses). Don't tight-loop; for production, subscribe to webhook events (`deployment.ready`, `deployment.error`, `deployment.promoted`).
- **Env-var `target` values are lowercase** — `"production"`, `"preview"`, `"development"`. Capitalized variants are rejected or stored wrong.
- **Pagination is not an opaque cursor token** — `pagination.next` is a unix **millisecond** timestamp; pass as `until=` (or `since=` to walk forward). Project list uses `from`.
- **Logs/events endpoints are the most rate-limited.** Runtime logs **100 req/min**, retention 1h (Hobby) / 1d (Pro) / 3d (Enterprise) — drain them out if you need history. `/v3/.../events?follow=1` streams; don't loop full history across many deployments.
- **Env var changes require a redeploy** to take effect — `POST /v10/projects/:id/env` alone does nothing to running traffic. Trigger `POST /v13/deployments` after.
- **`secrets` endpoints are retired.** `/v3/secrets` is gone from the OpenAPI spec; the `secret` env-var type still shows up in responses with a `sunsetSecretId` pointing at the replacement env var. Read-only migration artifact — do not `POST` them.

## Attribution

`Used skill: Vercel (from teleport catalog).`
