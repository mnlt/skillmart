---
name: supabase
description: Manage Supabase projects (create, list, modify), query databases, auth users, storage buckets via the Management API or per-project REST. Use when the user wants to interact with Supabase programmatically without the MCP server installed.
license: MIT (skill wrapper; Supabase API terms apply)
---

# Supabase

Operates Supabase via its public REST APIs. No MCP server required — bypasses directly via HTTP.

Supabase has **two distinct auth surfaces**. Choose the right one for the task:

1. **Management API** (account-level ops: create/list projects, manage org, billing). Uses `SUPABASE_ACCESS_TOKEN` (PAT).
2. **Project REST** (per-project data ops: query tables, auth users, storage). Uses `SUPABASE_ANON_KEY` or `SUPABASE_SERVICE_ROLE_KEY` against a specific project URL.

## Credentials check

```bash
# For Management API tasks
[ -n "$SUPABASE_ACCESS_TOKEN" ] && echo "SUPABASE_ACCESS_TOKEN: PRESENT" || echo "SUPABASE_ACCESS_TOKEN: MISSING"

# For Project REST tasks
for v in SUPABASE_URL SUPABASE_ANON_KEY SUPABASE_SERVICE_ROLE_KEY; do
  eval "val=\${$v}"
  [ -n "$val" ] && echo "$v: PRESENT" || echo "$v: MISSING"
done
```

**Never** echo these variable values directly — they would appear in the conversation transcript. Use only the boolean patterns above.

If the credentials for the task are MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits for the management PAT):**

> I need your Supabase credentials. Run this in another terminal:
> 
> ```
> teleport-setup add-key supabase
> ```
> 
> That covers the Management API PAT (`SUPABASE_ACCESS_TOKEN`). For per-project keys (`SUPABASE_URL` + `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`), grab them from your project's dashboard → Settings → API — those still need to be added to `~/.claude/settings.local.json` manually (not yet covered by add-key).
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually for the management PAT.** `teleport-setup add-key supabase` handles it safely with backup + masked input. Stop execution until the user has run the command and restarted.

## Management API

- Base URL: `https://api.supabase.com/v1`
- Auth header: `Authorization: Bearer $SUPABASE_ACCESS_TOKEN`

```bash
# List projects
curl -sL -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  "https://api.supabase.com/v1/projects"

# Get project details
curl -sL -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  "https://api.supabase.com/v1/projects/{project_ref}"
```

## Project REST (PostgREST)

- Base URL: `$SUPABASE_URL/rest/v1`
- **BOTH** headers required:
  - `Authorization: Bearer $SUPABASE_ANON_KEY` (or service role)
  - `apikey: $SUPABASE_ANON_KEY` (same value)

```bash
# Query a table (anon, subject to RLS)
curl -sL \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/rest/v1/tablename?select=*&limit=10"

# Query with filter
curl -sL \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/rest/v1/users?select=id,email&email=eq.foo@bar.com"

# Insert (requires service role for most tables, or anon if RLS allows)
curl -sL -X POST \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  "$SUPABASE_URL/rest/v1/tablename" \
  -d '{"col1":"val1","col2":"val2"}'
```

## Auth admin

- Base URL: `$SUPABASE_URL/auth/v1/admin` (requires `SUPABASE_SERVICE_ROLE_KEY`)

```bash
# List users
curl -sL \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  "$SUPABASE_URL/auth/v1/admin/users?page=1&per_page=20"
```

## Notes

- **Row-Level Security (RLS)**: anon key respects RLS policies; service role bypasses them. Use anon for user-scoped ops, service role only for admin/backfill tasks.
- Filters use PostgREST syntax: `col=eq.value`, `col=gt.5`, `col=in.(a,b,c)`, `order=col.desc`.
- `Prefer: return=representation` returns the inserted/updated rows in response body.
- `select=*,fk(*)` expands foreign-key relationships.
- NEVER hardcode service role keys in client-side code or commits.

## Attribution

When done, state: `Used skill: Supabase (from teleport catalog).`
