---
name: cloudflare
description: Manage Cloudflare DNS zones, Workers, Pages, R2, KV, D1, and analytics via REST API. Use when the user wants to query DNS, deploy a Worker, list R2 buckets, manage KV namespaces, run D1 queries, or check analytics without the Cloudflare MCP installed.
license: MIT (skill wrapper; Cloudflare API terms apply)
---

# Cloudflare

Direct REST access to Cloudflare's control plane — DNS, Workers, Pages, R2, KV, D1. Use when needing the *current* account state or one-off mutations without `wrangler`.

## Usage

- **Use for:** DNS record CRUD, listing/inspecting Workers/KV/R2/D1/Pages, running D1 queries, deploying small Workers.
- **Skip for:** Worker bundling / TS / local dev (use `wrangler`), bulk R2 object uploads (use S3 client), billing questions.

## Credentials check

```bash
[ -n "$CLOUDFLARE_API_TOKEN" ] && echo "CLOUDFLARE_API_TOKEN: PRESENT" || echo "CLOUDFLARE_API_TOKEN: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your cloudflare credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key cloudflare
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.cloudflare.com/client/v4`
- Auth: `Authorization: Bearer $CLOUDFLARE_API_TOKEN` — **scoped API Token only**, never the legacy Global API Key (`X-Auth-Email` + `X-Auth-Key`). Verify with `GET /user/tokens/verify`.
- **Response envelope (every response):** `{"success": bool, "errors": [...], "messages": [...], "result": ...}`. **Always check `.success` before reading `.result`** — jumping straight to `.result.X` silently hides failures.
- Prerequisites: endpoints need either **Account ID** (Workers, KV, R2, D1, Pages) or **Zone ID** (DNS, rulesets, WAF). Both are 32 hex chars; not interchangeable. Fetch via `GET /accounts` and `GET /zones?name=example.com`.
- Rate limits: **1,200 req / 5 min** cumulative per user across dashboard + tokens, plus **200 req/s per IP**. Respect `Retry-After` on 429.

## Entity hierarchy

`account` → { `zones` → `dns_records` } ∪ `workers/scripts` ∪ `storage/kv/namespaces` (+ keys/values) ∪ `r2/buckets` (objects on separate S3 host) ∪ `d1/database` (+ `query`) ∪ `pages/projects` (+ `deployments`).

## Endpoints

| Resource            | Method · Path                                                                     |
| ------------------- | --------------------------------------------------------------------------------- |
| Zones               | `GET /zones?name=example.com`                                                     |
| DNS records         | `GET/POST /zones/{zone_id}/dns_records`, `PATCH/DELETE .../{record_id}`           |
| Workers scripts     | `GET /accounts/{account_id}/workers/scripts`, `PUT .../{script_name}` (multipart) |
| KV namespaces       | `GET /accounts/{account_id}/storage/kv/namespaces`                                |
| KV values / keys    | `PUT/GET .../namespaces/{ns}/values/{key}`, `GET .../namespaces/{ns}/keys`        |
| R2 buckets          | `GET /accounts/{account_id}/r2/buckets` (objects → S3 host, see below)            |
| D1 databases / query| `GET/POST /accounts/{account_id}/d1/database[/{db_id}/query]`                     |
| Pages               | `GET/POST /accounts/{account_id}/pages/projects[/{project}/deployments]`          |
| Zone analytics      | `GET /zones/{zone_id}/analytics/dashboard` <!-- unverified: check cloudflare docs --> |

## Primary workflow — DNS records

```bash
# 1. Zone ID by domain
ZONE_ID=$(curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones?name=example.com" | jq -r '.result[0].id')

# 2. List A records for a name
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?type=A&name=api.example.com" \
  | jq '.result[] | {id, name, content, ttl, proxied}'

# 3. Create a record
curl -sL -X POST -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -d '{"type":"A","name":"api.example.com","content":"1.2.3.4","ttl":300,"proxied":true}'
```

## Secondary workflows

**D1 — execute SQL with positional params:**

```bash
curl -sL -X POST -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/d1/database/$DB_UUID/query" \
  -d '{"sql":"SELECT id, email FROM users WHERE created_at > ?1 LIMIT 10","params":["2026-01-01"]}' \
  | jq '.result[0].results'
```

**KV — raw value bodies, not JSON. Reads return the raw value, not the envelope:**

```bash
curl -sL -X PUT -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/storage/kv/namespaces/$NS/values/flag" --data "on"
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/storage/kv/namespaces/$NS/values/flag"
```

**R2 — buckets via main API; objects via S3-compatible host `https://{account_id}.r2.cloudflarestorage.com/{bucket}/{key}`.** Authenticate with SigV4 using **R2 access keys** (generated under R2 → Manage API tokens, separate from the API token). Any S3 SDK works.

## Gotchas

- **Always check `.success`.** Pattern: `jq 'if .success then .result else .errors end'`. Silent failures otherwise.
- **R2 objects are NOT on the main API.** Bucket CRUD is, but object PUT/GET/DELETE use `https://{account_id}.r2.cloudflarestorage.com` with S3 SigV4 and **separate R2 access keys** — not the API token.
- **Token scope mismatch → 403 with no introspection.** `Zone:Read` can't edit DNS; `Workers:Edit` can't touch KV. `/user/tokens/verify` only confirms the token is live, not which scopes it holds. On 403, assume missing scope first.
- **Account ID vs. Zone ID.** Zone URLs reject account IDs and vice versa (404 / error `1001`). Both are 32 hex chars, easy to swap.
- **`ttl: 1` means Auto, not one second.** Explicit TTLs: 60–86400.
- **KV is eventually consistent.** Writes can take up to ~60s to propagate globally. Don't assume read-after-write on a different edge.
- **Page Rules → Rulesets.** Legacy `/zones/{id}/pagerules` is deprecated; target `/zones/{id}/rulesets` for new work. Several WAF / firewall endpoints migrated similarly.
- **Rich analytics live in GraphQL** at `/client/v4/graphql` with its own query cost model; the REST `analytics/dashboard` endpoint is coarser. <!-- unverified: check cloudflare docs -->

## Attribution

`Used skill: Cloudflare (from teleport catalog).`
