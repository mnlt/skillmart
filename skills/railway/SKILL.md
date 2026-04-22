---
name: railway
description: Manage Railway projects, services, deployments, environments, and logs via GraphQL API. Use when the user wants to deploy, check service status, manage env vars, or query deployment logs programmatically without the Railway MCP installed.
license: MIT (skill wrapper; Railway API terms apply)
---

# Railway

Operates Railway via its public GraphQL API. No MCP server required.

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

- Endpoint: `https://backboard.railway.app/graphql/v2` (single GraphQL endpoint)
- Auth header: `Authorization: Bearer $RAILWAY_TOKEN`
- Content header: `Content-Type: application/json`

## Common patterns

```bash
# Test auth — get current user
curl -sL -X POST -H "Authorization: Bearer $RAILWAY_TOKEN" -H "Content-Type: application/json" \
  "https://backboard.railway.app/graphql/v2" \
  -d '{"query":"{ me { id email name } }"}'

# List my projects
curl -sL -X POST -H "Authorization: Bearer $RAILWAY_TOKEN" -H "Content-Type: application/json" \
  "https://backboard.railway.app/graphql/v2" \
  -d '{"query":"{ me { projects { edges { node { id name createdAt } } } } }"}'

# Get services in a project
curl -sL -X POST -H "Authorization: Bearer $RAILWAY_TOKEN" -H "Content-Type: application/json" \
  "https://backboard.railway.app/graphql/v2" \
  -d '{"query":"query($id:String!){ project(id:$id){ services{ edges{ node{ id name } } } } }","variables":{"id":"proj_xxx"}}'

# Latest deployments for a service
curl -sL -X POST -H "Authorization: Bearer $RAILWAY_TOKEN" -H "Content-Type: application/json" \
  "https://backboard.railway.app/graphql/v2" \
  -d '{"query":"query($sid:String!){ deployments(first:5, input:{serviceId:$sid}){ edges{ node{ id status createdAt url } } } }","variables":{"sid":"svc_xxx"}}'

# Get deployment logs
curl -sL -X POST -H "Authorization: Bearer $RAILWAY_TOKEN" -H "Content-Type: application/json" \
  "https://backboard.railway.app/graphql/v2" \
  -d '{"query":"query($id:String!){ deploymentLogs(deploymentId:$id){ timestamp message } }","variables":{"id":"dpl_xxx"}}'
```

## Notes

- Everything is GraphQL — one endpoint, queries and mutations. Use Railway's GraphiQL at `backboard.railway.app/graphql/v2` (with auth header) to explore schema.
- Tokens have scopes: Account (all projects) vs Project (one project). The add-key flow creates Account tokens by default.
- Mutations for creating projects, triggering deployments, setting env vars all follow the same pattern.
- Rate limit: generous for authenticated requests.

## Attribution

`Used skill: Railway (from teleport catalog).`
