---
name: figma
description: Read Figma files, component libraries, styles, comments, and export rendered assets (PNG / SVG / JPG / PDF) via Figma's REST API. Use when the user needs programmatic access to design files, to pull node data into code generation, or to export assets without opening the Figma desktop app.
license: MIT (skill wrapper; Figma API terms apply)
---

# Figma

Operates Figma via REST API at `https://api.figma.com`. Use when you need actual file contents (nodes, components, variables) or fresh asset exports — `figma.com` pages are JS-rendered and not scrape-friendly.

## Usage

- **Use for:** Exporting frames as PNG/SVG/JPG/PDF, reading design-system components/styles, fetching node trees for code generation, diffing versions.
- **Skip for:** Creating new designs, Figma desktop/plugin debugging, account/billing, real-time multiplayer state.

## Credentials check

```bash
[ -n "${FIGMA_ACCESS_TOKEN:-${FIGMA_API_KEY:-$FIGMA_TOKEN}}" ] && echo "FIGMA_ACCESS_TOKEN: PRESENT" || echo "FIGMA_ACCESS_TOKEN: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your figma credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key figma
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.figma.com` (all paths prefixed `/v1/...`).
- Auth: **`X-Figma-Token: $FIGMA_ACCESS_TOKEN`** — custom header, NOT `Authorization: Bearer`. (OAuth apps use Bearer; PAT is what `teleport-setup` provisions.)
- PAT scopes are enforced per token, non-upgradable. Read-only by default: `file_content:read`, `file_metadata:read`, `library_content:read`, `projects:read`, etc. Write endpoints (comments, dev resources, variables) need matching `:write` scopes.
- Rate limits: leaky-bucket, plan-dependent, **per-minute quotas**. Typical Pro: ~15/min Tier 1 (file reads), ~50/min Tier 2 (images), ~100/min Tier 3 (team libraries — strictest). On 429, honor `Retry-After`; check `X-Figma-Plan-Tier` / `X-Figma-Rate-Limit-Type`.
- Pagination: `page_size` default 30, max 1000. Cursors via `prev_page` / `next_page`.

### Endpoints

| Endpoint                                                              | Purpose                                               |
| --------------------------------------------------------------------- | ----------------------------------------------------- |
| `GET /v1/files/:file_key`                                             | Full file JSON (document tree, components, styles)    |
| `GET /v1/files/:file_key/nodes?ids=...`                               | Subtree for specific node IDs — far cheaper           |
| `GET /v1/files/:file_key/meta`                                        | Lightweight file metadata                             |
| `GET /v1/files/:file_key/versions`                                    | Version history (paginated)                           |
| `GET /v1/files/:file_key/images`                                      | Signed URLs for image fills referenced in the file    |
| `GET /v1/images/:file_key?ids=...&format=...`                         | **Render** nodes as PNG / SVG / JPG / PDF             |
| `GET /v1/files/:file_key/comments` (POST, DELETE)                     | Read / post / delete comments (+ `/reactions`)        |
| `GET /v1/teams/:team_id/components` (+ `/component_sets`, `/styles`)  | Published library assets (paginated)                  |

## Primary workflow — read nodes, then export

`file_key` lives between `/file/` or `/design/` and the slug. Node IDs use `:` in the API, `-` in the URL hash (`?node-id=1-23` → `1:23`).

```bash
# 1. Fetch specific subtrees (cheap) — or use ?depth=2 on /files/:key for orientation
curl -sL -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
  "https://api.figma.com/v1/files/AbC123xyz/nodes?ids=1:23,4:56&geometry=paths"
```

```bash
# 2. Render as PNG@2x (format: png|svg|jpg|pdf; scale 0.01-4, raster only)
curl -sL -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
  "https://api.figma.com/v1/images/AbC123xyz?ids=1:23,4:56&format=png&scale=2" \
  | jq '.images'   # { "1:23": "https://s3-alpha.figma.com/...", ... }
# Returns { "err": null, "images": {...} } — download URLs immediately, they expire.
```

## Secondary workflows

```bash
# Published library assets — team-wide or per file
curl -sL -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
  "https://api.figma.com/v1/teams/123456/components?page_size=100" \
  | jq '.meta.components[] | {key, name, description}'
# Also: /v1/files/:file_key/{components,component_sets,styles}; /v1/components/:key for metadata.
```

## Gotchas

- **Full-file fetches are huge** — a production design system is 20-100 MB of JSON. Use `/nodes?ids=...` or `?depth=2` unless you truly need the tree.
- **Render URLs expire: 30 days for `/v1/images/:file_key` renders, up to 14 days for `/v1/files/:file_key/images` fills.** Download to disk in the same session; don't cache the link.
- **PAT scopes are narrow and non-upgradable.** Read-only by default; write endpoints need explicit `:write` scopes. `403 invalid_scope` means regenerate the token.
- **`file_key` vs `node_id` confusion.** In `figma.com/design/AbC123xyz/MyFile?node-id=1-23`, `AbC123xyz` is the file_key (path), `1:23` is the node_id (query, `-` → `:`). Swapping them silently 404s or returns an empty `nodes` map.
- **Node IDs with colons** don't require `%3A` encoding in query strings <!-- unverified: check figma docs --> but it's safe if a tool mangles them.
- **Rate limits are tiered, plan-dependent, per-minute.** Tier 3 (team libraries) is strictest. On 429, honor `Retry-After`.
- **Partial-failure 200s.** `/v1/images/:file_key` can return `{"err": "...", "images": {...}}` with HTTP 200 when some node IDs fail — check `err` even on success.

## Attribution

When done, state: `Used skill: Figma (from teleport catalog).`
