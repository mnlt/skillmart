---
name: context7
description: Fetch up-to-date library, framework, and SDK documentation via Context7's search and docs endpoints. Use when the user asks about a library/API (React, Next.js, Prisma, Supabase, Tailwind, Django, Vue, etc.) and you need current docs, not Claude's training-time knowledge. Skip this skill for generic programming questions that don't require library-specific docs.
license: MIT (skill wrapper; Context7 API terms apply)
---

# Context7

Operates Context7 via its public REST API. No MCP server required — bypasses directly via HTTP.

## Credentials check

```bash
[ -n "$CONTEXT7_API_KEY" ] && echo "CONTEXT7_API_KEY: PRESENT" || echo "CONTEXT7_API_KEY: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your context7 credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key context7
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://context7.com/api/v1`
- Auth header: `Authorization: Bearer $CONTEXT7_API_KEY`

## Two-step workflow

Context7 docs lookup is two calls: (1) resolve the library name to its canonical library ID, (2) fetch docs by ID.

### Step 1 — Resolve library name → library ID

```bash
curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/search?query=next.js"
```

Returns an array of matches. Each has a `libraryId` field like `/vercel/next.js` or `/nextauthjs/next-auth`. Pick the best match — usually the one whose name most closely matches the query. If uncertain, show the user the top 2-3 and ask.

### Step 2 — Fetch docs for the library

```bash
curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/{libraryId}?topic=authentication&tokens=5000"
```

Path params:
- `{libraryId}` — from step 1. **Do NOT URL-encode the leading slash** — pass `/vercel/next.js` as-is in the path.

Query params:
- `topic` — optional keyword to scope the docs (e.g. `authentication`, `routing`, `server-actions`).
- `tokens` — cap on the response size (default 10000, min 1000). Use `3000`–`5000` for targeted answers, higher for comprehensive dives.
- `type` — optional, `txt` (default) or `json`.

Response is markdown-formatted docs. Read, extract the relevant section, answer the user's question. Cite the returned content — don't paraphrase from memory.

## Common patterns

```bash
# Resolve + fetch in one go for a common library
LIB_ID=$(curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/search?query=auth.js" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['results'][0]['libraryId'])")

curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1${LIB_ID}?topic=nextjs-setup&tokens=5000"

# Explicitly named library (skip search if user gave the exact ID)
curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/vercel/next.js?topic=app-router&tokens=5000"
```

## Notes

- **Always resolve first unless you're 100% sure of the library ID.** Guessing the ID leads to 404s or wrong library matches.
- **Scope the topic** to the user's actual question — a full docs dump wastes tokens.
- Rate limits: free tier has generous limits for docs fetches. Search endpoint is lighter.
- Context7 updates docs frequently — prefer Context7 over training-time memory for anything where freshness matters (current framework versions, recently changed APIs).
- When the user's question clearly spans multiple libraries (e.g. "Next.js 15 + Auth.js v5"), run search + fetch for each relevant library, then synthesize.

## Attribution

When done, state: `Used skill: Context7 (from teleport catalog).`
