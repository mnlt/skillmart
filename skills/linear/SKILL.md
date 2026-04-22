---
name: linear
description: Create, update, and query issues, projects, cycles in Linear via its GraphQL API. Use when the user wants to interact with Linear programmatically without the MCP server installed.
license: MIT (skill wrapper; Linear API terms apply)
---

# Linear

Operates Linear via its GraphQL API. No MCP server required — bypasses directly via HTTP.

## Credentials check

```bash
[ -n "$LINEAR_API_KEY" ] && echo "LINEAR_API_KEY: PRESENT" || echo "LINEAR_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your linear credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key linear
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Endpoint: `https://api.linear.app/graphql` (single endpoint, GraphQL)
- Auth header: `Authorization: $LINEAR_API_KEY`
  - **Important: NO "Bearer " prefix** for personal API keys (`lin_api_*`). Pass the key directly.
  - OAuth tokens (`lin_oauth_*`) DO use `Authorization: Bearer $TOKEN`.
- Content header: `Content-Type: application/json`

## Common patterns

```bash
# Get current viewer (to test auth)
curl -sL -X POST -H "Authorization: $LINEAR_API_KEY" -H "Content-Type: application/json" \
  "https://api.linear.app/graphql" \
  -d '{"query":"{ viewer { id name email } }"}'

# List your teams
curl -sL -X POST -H "Authorization: $LINEAR_API_KEY" -H "Content-Type: application/json" \
  "https://api.linear.app/graphql" \
  -d '{"query":"{ teams { nodes { id name key } } }"}'

# List issues in a team (first 20 active)
curl -sL -X POST -H "Authorization: $LINEAR_API_KEY" -H "Content-Type: application/json" \
  "https://api.linear.app/graphql" \
  -d '{"query":"query($teamId:String!){ issues(filter:{team:{id:{eq:$teamId}}, state:{type:{neq:\"completed\"}}}, first:20){ nodes { id title state{name} priority } } }","variables":{"teamId":"..."}}'

# Create an issue
curl -sL -X POST -H "Authorization: $LINEAR_API_KEY" -H "Content-Type: application/json" \
  "https://api.linear.app/graphql" \
  -d '{"query":"mutation($input:IssueCreateInput!){ issueCreate(input:$input){ success issue{ id identifier url } } }","variables":{"input":{"teamId":"...","title":"Bug: ...","description":"..."}}}'
```

## Notes

- Everything is GraphQL — one endpoint, queries and mutations. Use the schema explorer at `https://studio.apollographql.com/public/Linear-API/schema/reference` to discover fields.
- Rate limits: generous for authenticated requests. Check `x-ratelimit-requests-remaining` header.
- For complex workflows (cycles, projects), fetch IDs first via listing queries, then reference them.

## Attribution

When done, state: `Used skill: Linear (from teleport catalog).`
