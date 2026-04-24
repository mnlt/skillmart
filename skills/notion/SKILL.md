---
name: notion
description: Read and write Notion pages, databases, and blocks via the public REST API — query a database with filters, create/update pages, append block content, search the workspace. Use when the user wants an agent to interact with their Notion workspace (e.g., a tasks or docs database) without the MCP server installed.
license: MIT (skill wrapper; Notion API terms apply)
---

# Notion

Direct REST access to Notion pages, databases, blocks, and search — no MCP server. Use when the user wants the agent to query or mutate their workspace (e.g. a tasks DB). The hard part is the response shapes, not auth: property values are wrapped per-type and text is rich-text arrays, not strings.

## Usage

- **Use for:** Querying a database with filters, creating/updating pages, appending blocks to a page, workspace search.
- **Skip for:** Static markdown exports, bulk imports of thousands of rows (script with real pagination), realtime sync/webhooks (API is pull-based).

## Credentials check

```bash
[ -n "${NOTION_API_KEY:-${NOTION_TOKEN:-$NOTION_INTEGRATION_TOKEN}}" ] && echo "NOTION_API_KEY: PRESENT" || echo "NOTION_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your notion credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key notion
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.notion.com/v1`
- Auth: `Authorization: Bearer $NOTION_API_KEY`
- **`Notion-Version: 2026-03-11` header is REQUIRED** — missing it returns `400 missing_version`.
- Content-Type: `application/json` on POST/PATCH.
- Rate limit: ~3 req/s per integration; `429 rate_limited` + `Retry-After` on excess. Payload caps: 500KB, 100 items per array, 2000 chars per rich-text object.
- **Permissions:** auth alone is not enough. The integration must be explicitly shared with each page/database (page `•••` → Connections → add integration). Unshared = `404 object_not_found`.

## Object model

Three objects: **page** (has `properties` map if in a database, `parent` tells location; content blocks are NOT returned — separate `GET /blocks/{page_id}/children`), **database** (has `properties` schema: column name → type def; exactly one `title` column), **block** (ordered children on any page; 30+ types incl. `paragraph`, `heading_1/2/3`, `to_do`, `toggle`, `code`, `callout`, `image`, `table`). Text-bearing fields are always **arrays of rich-text objects**, never plain strings — on write, only `text.content` is required.

### Property write shape (wrapper inner key MUST match column type)

| Column type                      | Write shape                                                                |
| -------------------------------- | -------------------------------------------------------------------------- |
| `title` / `rich_text`            | `{"title": [{"text": {"content": "Hello"}}]}`                              |
| `number`                         | `{"number": 42}`                                                           |
| `select` / `status`              | `{"select": {"name": "Done"}}` — name OR id                                |
| `multi_select`                   | `{"multi_select": [{"name": "A"}, {"name": "B"}]}`                         |
| `date`                           | `{"date": {"start": "2026-04-24", "end": null, "time_zone": null}}`        |
| `checkbox`                       | `{"checkbox": true}`                                                       |
| `relation` / `people`            | `{"relation": [{"id": "page-uuid"}]}` — UUIDs only                         |
| `url` / `email` / `phone_number` | `{"url": "https://..."}` (raw string)                                      |
| `formula` / `rollup`             | **Read-only** — computed by Notion                                         |

Bare strings like `{"Name": "Hello"}` always 400. You need `{"Name": {"title": [{"text": {"content": "Hello"}}]}}`.

## Endpoints

| Resource   | Method · Path                                                               |
| ---------- | --------------------------------------------------------------------------- |
| Databases  | `POST /databases/{id}/query`, `GET/POST/PATCH /databases/{id}`              |
| Pages      | `GET /pages/{id}`, `POST /pages`, `PATCH /pages/{id}`                       |
| Properties | `GET /pages/{id}/properties/{prop_id}` (single prop when >25 entries)       |
| Blocks     | `GET/PATCH /blocks/{id}/children`, `PATCH/DELETE /blocks/{id}`              |
| Search     | `POST /search` (workspace-wide, pages + data sources)                       |
| Users      | `GET /users`, `/users/{id}`, `/users/me` (`me` = the bot itself)            |

## Primary workflow — query a database, then create a page

```bash
# Query with compound filter + sort + pagination
curl -sL -X POST -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2026-03-11" -H "Content-Type: application/json" \
  "https://api.notion.com/v1/databases/{database_id}/query" \
  -d '{"filter": {"and": [
         {"property": "Status", "select": {"equals": "In progress"}},
         {"property": "Due",    "date":   {"on_or_before": "2026-04-30"}}
       ]},
       "sorts": [{"property": "Due", "direction": "ascending"}],
       "page_size": 100, "start_cursor": "<next_cursor-if-any>"}'
# Response: {results: [pages...], next_cursor, has_more}. Loop until has_more=false.

# Create a page (property keys must match schema, case-sensitive)
curl -sL -X POST -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2026-03-11" -H "Content-Type: application/json" \
  "https://api.notion.com/v1/pages" \
  -d '{"parent": {"database_id": "{database_id}"},
       "properties": {
         "Name":   {"title": [{"text": {"content": "Ship v2"}}]},
         "Status": {"select": {"name": "In progress"}},
         "Due":    {"date": {"start": "2026-05-01"}}},
       "children": [
         {"object":"block","type":"paragraph",
          "paragraph":{"rich_text":[{"text":{"content":"Kickoff notes."}}]}}]}'
```

Filter operators are per-property-type (mirror the write wrappers): `select`/`status` → `{equals, does_not_equal, is_empty}`; `multi_select` → `{contains, does_not_contain}`; `date` → `{equals, before, on_or_before, past_week: {}, next_month: {}}`; compound `{and: [...]}` / `{or: [...]}` nests up to two levels.

To update: `PATCH /pages/{id}` with only the properties to change, e.g. `{"properties": {"Status": {"select": {"name": "Done"}}}}`. To append blocks: `PATCH /blocks/{page_id}/children` with `{"children": [block, ...]}` (max 100 per call).

## Gotchas

- **Property values MUST be wrapped by type.** `{"Name": "Hello"}` fails; `title` needs `{"title": [{"text": {"content": "Hello"}}]}`. Single most common bug.
- **"Page not found" 404s usually mean "integration not shared."** Silent — the API treats unshared and nonexistent identically. Fix in UI: page `•••` → Connections → add.
- **`Notion-Version: 2026-03-11` is mandatory.** Omitting returns `400 missing_version`. Bump deliberately after reading the changelog.
- **Block children are one level deep per call.** `has_children: true` hides the subtree — recurse `GET /blocks/{id}/children` for nested toggles, columns, lists until exhausted.
- **Pagination is cursor-based, mandatory on every list endpoint.** 100-item max; loop `start_cursor` ← previous `next_cursor` until `has_more: false`. Don't assume one call returns everything.
- **Rich-text content caps at 2000 chars per object.** Split longer strings across multiple rich-text entries in the array.
- **Rate limit ~3 req/s per integration.** Parallel curls trip 429; serialize or respect `Retry-After`.
- **Formula and rollup are read-only** — sending values on create/update will 400 or be silently ignored.

## Attribution

When done, state: `Used skill: Notion (from teleport catalog).`
