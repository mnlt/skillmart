---
name: railway
description: Manage Railway projects, services, deployments, environments, variables, and deployment logs via Railway's public GraphQL API — one endpoint, relay-style pagination, two token flavors (account vs project), typed mutations for deploys and env vars. Use when the user wants to deploy, check service status, manage env vars, or read deployment logs programmatically without the Railway MCP installed.
license: MIT (skill wrapper; Railway API terms apply)
---

# Railway

Operates Railway via its public **GraphQL** API. Covers projects, environments, services, deployments, variables, logs. Prefer over `railway` CLI for typed, filterable reads pipeable through `jq`.

## Usage

- **Use for:** Listing projects/services/deploy status, tailing deployment logs, upserting env vars, triggering redeploys from scripts.
- **Skip for:** New-account setup, billing/plan changes, first-time GitHub OAuth, short interactive sessions where `railway` CLI is faster.

## Credentials check

```bash
[ -n "$RAILWAY_TOKEN" ] && echo "RAILWAY_TOKEN: PRESENT" || echo "RAILWAY_TOKEN: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your railway credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key railway
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Endpoint: `https://backboard.railway.com/graphql/v2` — single endpoint, POST only, `Content-Type: application/json`.
- Auth: `Authorization: Bearer $RAILWAY_TOKEN` (account/workspace/OAuth tokens).
- **Token flavors:** account/workspace/OAuth use `Authorization: Bearer`; **project tokens use `Project-Access-Token: <TOKEN>` (NOT Bearer)** and see only one project+env. This skill assumes `$RAILWAY_TOKEN` is an **account token**.
- Rate limits: 100/1000/10000 RPH (Free/Hobby/Pro), 10/50 RPS (Hobby/Pro). Inspect `X-RateLimit-Remaining`, `Retry-After`.
- **GraphQL envelope:** `{ "data":{...}, "errors":[...] }`. HTTP 200 even on failure — always check `.errors`. Variables go in top-level `variables`, not interpolated. Relay-style `{ edges:[{node}], pageInfo }` on lists.
- Introspection enabled; GraphiQL at `https://railway.com/graphiql`.

## Entity hierarchy

`Workspace` → `Project` → `Environment` + `Service` → `Deployment`. Variables scoped by triple `(projectId, environmentId, serviceId)`; omit `serviceId` for project-shared.

## Queries & mutations

| Operation                                               | Kind     | One-liner                                                      |
| ------------------------------------------------------- | -------- | -------------------------------------------------------------- |
| `me`                                                    | query    | Current user; auth smoke test.                                 |
| `projects` / `project(id:)` / `environments(projectId:)`| query    | List/fetch projects + their envs and services.                 |
| `deployments(input:, first:)` / `deployment(id:)`       | query    | Recent deploys for `(projectId, serviceId)`; single `{status,url,createdAt}`. |
| `deploymentLogs(deploymentId:, limit:)`                 | query    | Log lines `{timestamp,message,severity}` — `limit` required.   |
| `variables(projectId:, environmentId:, serviceId:)`     | query    | Variables for a scope.                                         |
| `projectCreate` / `serviceCreate` / `environmentCreate` | mutation | Create primitives.                                             |
| `serviceInstanceDeploy` / `serviceInstanceUpdate`       | mutation | Trigger build+deploy; change start/build cmd, replicas, region. |
| `variableCollectionUpsert` / `deploymentRollback(id:)`  | mutation | Bulk-upsert env vars; roll a deployment back.                  |

<!-- unverified: older guides mention `deploymentRestart`, `deploymentRemove`, `deploymentTriggerCreate`; current cookbook lists `serviceInstanceDeploy` and `deploymentRollback`. `serviceInstanceDeployV2` also seen in some deployments. Check docs for current mutation name. -->

## Primary workflows

All calls: POST to `$URL=https://backboard.railway.com/graphql/v2` with `$H = -H "Authorization: Bearer $RAILWAY_TOKEN" -H "Content-Type: application/json"`.

**1. List projects, environments, services**

```bash
curl -sL -X POST $H "$URL" \
  -d '{"query":"query Me { me { projects(first:20){ edges{ node{ id name environments{ edges{ node{ id name } } } services{ edges{ node{ id name } } } } } } } }"}' \
  | jq '.data.me.projects.edges[].node | {id, name, envs:[.environments.edges[].node.name], services:[.services.edges[].node.name]}'
```

Save each `environment.id` / `service.id` — every mutation needs them; IDs are opaque UUIDs.

**2. Upsert env vars (bulk)**

```bash
curl -sL -X POST $H "$URL" \
  -d '{"query":"mutation($input:VariableCollectionUpsertInput!){ variableCollectionUpsert(input:$input) }","variables":{"input":{"projectId":"proj_xxx","environmentId":"env_xxx","serviceId":"svc_xxx","variables":{"LOG_LEVEL":"debug"},"replace":false,"skipDeploys":false}}}'
```

`replace:true` wipes vars not in payload; `skipDeploys:true` upserts without redeploying.

**3. Trigger a deploy**

```bash
curl -sL -X POST $H "$URL" \
  -d '{"query":"mutation($s:String!,$e:String!){ serviceInstanceDeploy(serviceId:$s, environmentId:$e) }","variables":{"s":"svc_xxx","e":"env_xxx"}}'
```

Confirm via `deployments(input:{serviceId:$s}, first:1)`. Status: `Initializing → Building → Deploying → Active/Completed` (or `Failed/Crashed`). Poll ≥5s.

## Gotchas

- **GraphQL errors return HTTP 200.** Always check `.errors` before trusting `.data`; `curl -f` won't save you.
- **Account vs project tokens silently mismatch.** Different header names *and* different scopes. A project token used as Bearer, or cross-project queries on a project token, fail with opaque auth errors.
- **Variable scope is a triple** `(projectId, environmentId, serviceId)`. Omitting `serviceId` creates a project-shared var; per-service inheritance depends on settings — don't assume propagation.
- **Mutation names drift.** Railway has renamed deployment mutations (older `deploymentTriggerCreate` → current `serviceInstanceDeploy`). "Field not found" → re-check the cookbook. <!-- unverified -->
- **Log rate limits are tight.** Don't poll `deploymentLogs` in a tight loop; one read per 5–10s, increase `limit` instead.
- **Relay cursor pagination.** List fields return `{ edges:[{node}], pageInfo:{endCursor, hasNextPage} }`. Use `first:N, after:"<cursor>"`; always pass `first` explicitly.
- **Use introspection.** Point GraphiQL at the endpoint with your token and auto-complete the schema instead of guessing.

## Attribution

`Used skill: Railway (from teleport catalog).`
