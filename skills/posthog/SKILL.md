---
name: posthog
description: Query PostHog product analytics via REST API — event analytics, HogQL SQL queries, feature flags, experiments, session recordings, insights, persons, cohorts. Use when the user wants to answer an analytics question, toggle/inspect a flag, or pull event data programmatically without opening the PostHog UI or installing the PostHog MCP.
license: MIT (skill wrapper; PostHog API terms apply)
---

# PostHog

Operates PostHog via REST API — event analytics, **HogQL queries**, feature flags, experiments, session recording metadata, insights, persons. Supports US cloud, EU cloud, and self-hosted. No MCP server required.

## Usage

- **Use for:** HogQL queries ("how many `$pageview` last 7d?"), flag inspect/toggle, last-N events for a user, experiment results.
- **Skip for:** Debugging client-side tracking, raw event ingestion (use an SDK), concept questions, raw replay JSON export (UI-only).

## Credentials check

```bash
[ -n "${POSTHOG_PERSONAL_API_KEY:-$POSTHOG_API_KEY}" ] && echo "POSTHOG_API_KEY: PRESENT" || echo "POSTHOG_API_KEY: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your posthog credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key posthog
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL varies: US `https://us.posthog.com`, EU `https://eu.posthog.com`, self-hosted `https://{your-host}`. Default to US; switch on explicit user confirmation or 401.
- Auth: `Authorization: Bearer $POSTHOG_PERSONAL_API_KEY` (key format `phx_*`).
- Most endpoints are **project-scoped**: `/api/projects/{project_id}/...`. Get ids via `GET /api/projects/`. Newer `/api/environments/{id}/...` routes coexist; prefer `projects`. <!-- unverified: /projects/ vs /environments/ deprecation timeline -->
- Personal API keys carry **scopes** (`query:read`, `feature_flag:read/write`, `insight:read/write`, `event:read`, `person:read/write`, `experiment:read/write`, etc.). Wrong scope = silent 403 or filtered result. <!-- unverified: canonical scope list -->
- Rate limits (team-wide): Query 2400/hr · Analytics 240/min + 1200/hr · Events 60/min + 300/hr · Flag local-eval 600/min · CRUD 480/min + 4800/hr.

## Endpoints

| Endpoint (under `/api/projects/{project_id}`) | Purpose                                                 |
| --------------------------------------------- | ------------------------------------------------------- |
| `POST /query/`                                | Run HogQL (primary)                                     |
| `GET /events/`                                | Raw events (**deprecated**; use `/query/`)              |
| `/feature_flags/`                             | List / create / update / soft-delete flag definitions   |
| `/insights/` / `/dashboards/`                 | Saved charts and dashboards                             |
| `/persons/` / `/cohorts/`                     | Users and audience definitions                          |
| `/session_recordings/`                        | Recording **metadata** only (raw replay is UI-only)     |
| `/experiments/` / `/actions/`                 | Experiments CRUD; named event patterns (legacy)         |

## Primary workflow — HogQL query

HogQL is PostHog's SQL dialect (**Clickhouse-flavored, not PostgreSQL**). Almost every analytics question is one POST away.

```bash
curl -sL -X POST -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" -H "Content-Type: application/json" \
  "https://us.posthog.com/api/projects/$PROJECT_ID/query/" \
  -d '{"query":{"kind":"HogQLQuery","query":"SELECT event, count() AS c FROM events WHERE timestamp > now() - INTERVAL 7 DAY GROUP BY event ORDER BY c DESC LIMIT 20"}}'
```

Response: `results` (row tuples), `columns`, `types`, `hasMore` (cap hit), plus `is_cached`/`timings`/`cache_key` when cached.

## Secondary workflows

**Evaluate a flag for a user (server-side)** — uses the **project token** `phc_*` (not the personal key), on the `/flags/` endpoint (successor to legacy `/decide/`). <!-- unverified: /flags/ vs /decide/ current state -->

```bash
curl -sL -X POST -H "Content-Type: application/json" \
  "https://us.posthog.com/flags/?v=2" \
  -d '{"api_key":"phc_PROJECT_TOKEN","distinct_id":"alice@example.com"}'
```

**List insights / manage flags / fetch recording metadata:**

```bash
curl -sL -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  "https://us.posthog.com/api/projects/$PROJECT_ID/insights/?limit=20" | jq '[.results[] | {id, name, short_id}]'

curl -sL -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  "https://us.posthog.com/api/projects/$PROJECT_ID/feature_flags/" | jq '[.results[] | {id, key, active}]'
```

## Gotchas

- **Scope mismatch = silent 403 or filtered result.** Personal API keys carry scopes — one you didn't tick shows up as 403 without a clear error. First suspect when a key "works elsewhere but not here".
- **US vs EU host mismatch.** A key minted on US returns 401 against `eu.posthog.com` (and vice versa). Confirm the cloud before debugging anything else.
- **HogQL is Clickhouse-flavored, not PostgreSQL.** Date functions (`now()`, `INTERVAL 7 DAY`, `toDate()`, `toStartOfDay()`), string ops, and aggregates differ from Postgres. On "unknown function", check HogQL docs — don't assume Postgres.
- **Project ID vs team ID vs environment ID.** All three are numeric, appear in URLs, easy to conflate. Prefer `/api/projects/{id}/...`; pick one form and stick with it in a session.
- **Events are eventually consistent** — a just-ingested event may not appear in queries for ~30–60s. Wait before assuming capture failed. <!-- unverified: exact ingestion lag SLA -->
- **`/flags/` evaluation vs flag management.** `/flags/` (and legacy `/decide/`) use the **project token** `phc_*` to *evaluate* per-user. `/api/projects/{id}/feature_flags/` uses the **personal API key** `phx_*` to manage definitions. Different endpoints, different auth. <!-- unverified: /decide/ deprecation state -->
- **`POSTHOG_API_KEY` (`phc_*`) vs `POSTHOG_PERSONAL_API_KEY` (`phx_*`).** `phc_*` = public project token for SDK *ingestion* (write-only, safe in browsers). `phx_*` = personal key for private read/admin. Never ship `phx_*` to a browser.
- **`/api/events/` is deprecated.** Without `after` it returns only last 24h, offset caps at 50 000. Use `POST /query/` over the `events` table instead.

## Attribution

`Used skill: PostHog (from teleport catalog).`
