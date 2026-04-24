---
name: supabase
description: Operate Supabase via its two REST surfaces — the Management API (org/project admin) and per-project APIs (PostgREST database queries, Auth, Storage, Realtime, Edge Functions). Use when the user wants to list/create projects, fetch project API keys, or read/write their database without the MCP server installed.
license: MIT (skill wrapper; Supabase API terms apply)
---

# Supabase

Direct HTTP against Supabase's REST APIs — no MCP server required. **Two distinct API surfaces on different hosts with different auth.** Picking the wrong one is the single most common failure mode; internalize the split before sending any request.

## Usage

- **Use for:** Listing projects / fetching API keys, PostgREST table reads/writes, auth admin, storage bucket CRUD.
- **Skip for:** Concept questions (RLS theory), direct `psql` over `postgres://…`, debugging user's supabase-js code, schema design.

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

## The two-surface split — read this first

| Surface               | Base URL                          | Auth header(s)                                                                                            | Env vars                                                           |
| --------------------- | --------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Management API**    | `https://api.supabase.com/v1/...` | `Authorization: Bearer $SUPABASE_ACCESS_TOKEN`                                                            | `SUPABASE_ACCESS_TOKEN` (personal access token)                    |
| **Per-project REST**  | `$SUPABASE_URL/rest/v1/...`       | **Both:** `apikey: $KEY` AND `Authorization: Bearer $KEY` (same value in both)                            | `SUPABASE_URL` + `SUPABASE_ANON_KEY` or `SUPABASE_SERVICE_ROLE_KEY` |
| **Per-project Auth**  | `$SUPABASE_URL/auth/v1/...`       | Same two-header pattern                                                                                   | Same as REST                                                       |
| **Per-project Storage** | `$SUPABASE_URL/storage/v1/...`  | Same two-header pattern                                                                                   | Same as REST                                                       |

`SUPABASE_URL` looks like `https://{ref}.supabase.co` — `{ref}` is also the `{ref}` path segment in Management URLs. Extract from the subdomain if only the URL was given.

## Anon key vs service_role key

- **`SUPABASE_ANON_KEY`** — client-safe JWT. Respects Row Level Security (RLS). Safe for browsers/mobile. Empty responses when RLS filters rows.
- **`SUPABASE_SERVICE_ROLE_KEY`** — **bypasses RLS entirely.** Full read/write on every table. **Server-side only.** Leaking it = total DB compromise.
- Debugging "rows are empty"? Almost always RLS. Retry with service_role to confirm, then fix the policy — don't ship the service role.

## Endpoints

- **Management API** (`api.supabase.com/v1`): `/projects`, `/projects/{ref}`, `/projects/{ref}/api-keys`, plus orgs/members/branches/DB migrations. <!-- unverified: full Management API endpoint list at https://supabase.com/docs/reference/api -->
- **PostgREST** (`/rest/v1/{table}`): auto-generated from `public` schema. Methods: `GET` (select), `POST` (insert / upsert), `PATCH` (update), `DELETE`.
- **Auth** (`/auth/v1/`): `signup`, `token?grant_type=password|refresh_token`, `admin/users`.
- **Storage** (`/storage/v1/`): `bucket`, `object/{bucket}/{path}`.

## Primary workflows

**1. SELECT with projection, filter, order, limit** — filter syntax is `column=op.value`; operators include `eq`, `neq`, `gt`/`gte`, `lt`/`lte`, `like`/`ilike` (URL-encode `%` as `%25`), `in.(a,b,c)`, `is.null`. Multiple filters AND.

```bash
curl -sL \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  "$SUPABASE_URL/rest/v1/users?select=id,name,email&status=eq.active&order=created_at.desc&limit=50"
```

**2. INSERT / UPSERT** — `Prefer` shapes the response (`return=representation` = full row, `return=headers-only` = id in `Location`, `return=minimal` = empty default). Upsert requires `resolution=merge-duplicates` + `on_conflict`.

```bash
# INSERT returning the created row
curl -sL -X POST -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" -H "Prefer: return=representation" \
  "$SUPABASE_URL/rest/v1/users" -d '{"name":"Ada","email":"ada@example.com"}'

# UPSERT on a unique column
curl -sL -X POST -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: resolution=merge-duplicates,return=representation" \
  "$SUPABASE_URL/rest/v1/users?on_conflict=email" \
  -d '[{"email":"ada@example.com","name":"Ada v2"}]'
```

**3. UPDATE / DELETE** — filter is required or it hits every row.

```bash
curl -sL -X PATCH -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  "$SUPABASE_URL/rest/v1/users?id=eq.123" -d '{"name":"New name"}'

curl -sL -X DELETE -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  "$SUPABASE_URL/rest/v1/users?id=eq.123"
```

**4. Management: list projects / fetch keys**

```bash
curl -sL -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  "https://api.supabase.com/v1/projects/{ref}/api-keys"
```

## Gotchas

- **Wrong surface → opaque 401/404.** Management token sent to `{ref}.supabase.co/rest/v1` fails silently; anon key sent to `api.supabase.com` does too. First question on a 401: "am I on the right host?"
- **PostgREST needs BOTH headers with the same value.** `apikey` alone or `Authorization` alone is rejected. Both carry the same JWT (anon or service_role).
- **`service_role` bypasses RLS — never use from untrusted contexts.** Leaked = full DB.
- **Empty response usually means RLS, not empty table.** If an anon query returns `[]` and you expect rows, swap in service_role to confirm, then fix the policy.
- **Filter syntax is `column=op.value`, not `column=value`.** Forgetting the `eq.` prefix silently turns the filter into a query param PostgREST ignores.
- **`Prefer` header controls response shape.** Default is `return=minimal` (empty body). Add `return=representation` when you need the written row back.
- **Upsert needs `Prefer: resolution=merge-duplicates` + `on_conflict=<col>`.** Without `on_conflict`, upsert matches on PK; `resolution=ignore-duplicates` skips instead of merges.
- **Project ref lives in two places.** Subdomain of `SUPABASE_URL` (`https://{ref}.supabase.co`) AND `{ref}` path segment in Management URLs. Extract from the URL if the user only gave you one.

## Attribution

When done, state: `Used skill: Supabase (from teleport catalog).`
