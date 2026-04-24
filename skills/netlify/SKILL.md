---
name: netlify
description: Operate Netlify's REST API (sites, deploys, builds, env vars, forms, DNS). Use programmatically without Netlify MCP.
license: MIT (skill wrapper; Netlify API terms apply)
---

# Netlify

Operates Netlify via REST API. Covers sites, deploys, builds, functions, env vars, forms, DNS. Use when needing the *current* account state.

## Usage

- **Use for:** Checking deploy status, triggering builds, rotating env vars, reading forms, managing Netlify DNS.
- **Skip for:** Editing app source code, other providers (Vercel, etc.), local config tweaks (`netlify.toml`), external DNS.

## Credentials check

```bash
[ -n "${NETLIFY_AUTH_TOKEN:-$NETLIFY_PERSONAL_TOKEN}" ] && echo "NETLIFY_TOKEN: PRESENT" || echo "NETLIFY_TOKEN: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your netlify credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key netlify
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.netlify.com/api/v1`
- Auth: `Authorization: Bearer $NETLIFY_AUTH_TOKEN`
- Content-Type: `application/json` (writes); `application/octet-stream` or `application/zip` (file uploads).
- Pagination: `?page=` (1-indexed) + `?per_page=` (max 100). Parse `Link` header for `rel="next"`.
- Rate limits: 500 req/min general; **deploys stricter — 3/min + 100/day**. Check `X-RateLimit-*` headers.

## Entity hierarchy

`team` → `site` (UUID or slug `name`) → `deploy` / `build` / `function` / `form` + `submissions` / env vars / `hooks` / `build_hooks`. `dns_zones` → `dns_records` are account-scoped.

## Endpoints

| Resource  | Method · Path                                                                       |
| --------- | ----------------------------------------------------------------------------------- |
| Sites     | `GET /sites`, `GET/PATCH/DELETE /sites/{site_id}`, `POST /sites`                    |
| Deploys   | `GET /sites/{site_id}/deploys`, `GET /deploys/{deploy_id}`, `POST /sites/{site_id}/deploys` |
| Builds    | `POST /sites/{site_id}/builds`, `GET /sites/{site_id}/builds`                       |
| Env vars  | `GET/POST /accounts/{account_id}/env`, `PATCH/DELETE .../env/{key}`                 |
| Functions | `GET /sites/{site_id}/functions`, `GET /sites/{site_id}/functions/{name}`           |
| Forms     | `GET /sites/{site_id}/forms`, `GET /sites/{site_id}/submissions`, `GET /forms/{id}/submissions` |
| DNS       | `GET /dns_zones`, `GET /dns_zones/{id}`, `GET/POST /dns_zones/{id}/dns_records`, `DELETE .../{rec_id}` |
| Hooks     | `GET/POST /sites/{site_id}/hooks`, `GET/POST /sites/{site_id}/build_hooks`          |

## Primary workflows

**1. Inspect latest deploy status**

```bash
curl -sL -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/sites/${SITE_ID}/deploys?per_page=1" \
  | jq '.[0] | {id, state, deploy_url, commit_ref, error_message, created_at}'
```

**2. Trigger a deploy**

```bash
# Build hook (no auth; returns "ok", no deploy data)
curl -sL -X POST "https://api.netlify.com/build_hooks/${HOOK_ID}"

# API (Bearer token; counts against 3/min + 100/day)
curl -sL -X POST -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.netlify.com/api/v1/sites/${SITE_ID}/builds" -d '{}'
```

**3. Set env var (multi-context)**

```bash
curl -sL -X POST -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  "https://api.netlify.com/api/v1/accounts/${ACCOUNT_ID}/env?site_id=${SITE_ID}" \
  -d '[{"key":"MY_VAR","scopes":["builds","functions","runtime"],"values":[{"value":"prod-val","context":"production"},{"value":"prev-val","context":"deploy-preview"}]}]'
```

## Gotchas

- **`site_id` polymorphism:** most GETs accept UUID or `name` slug; some writes strictly require UUID. Resolve via `GET /sites?name=...` when in doubt.
- **Env vars are multi-valued per context** (`production`, `deploy-preview`, `branch-deploy`, `dev`). Don't collapse.
- **Deploy states:** `new`, `enqueued`, `building`, `uploading`, `uploaded`, `processing`, `prepared`, `ready`, `error`, `skipped`, `cancelled`. Poll ≥3-5s; don't tight-loop.
- **Build hooks return no `deploy_id`** — track by polling `/sites/{id}/deploys?per_page=1` after triggering.
- **Pagination is `Link`-header based.** Missing `rel="next"` = done. Don't synthesize `?page=N+1`; past the last page you get `[]`, not 404.
- **Deploy limits: 3/min, 100/day per account.** 429s deploys specifically while other calls still work.
- **Large file uploads** use the digest flow (`POST` with `files` digest → `PUT` each returned URL). Don't inline megabytes.
- **SAML-SSO teams reject PATs by default** — regenerate with "Allow access to my SAML-based Netlify team" checked.

## Attribution

When done, state: `Used skill: Netlify (from teleport catalog).`
