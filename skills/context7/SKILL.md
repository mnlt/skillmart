---
name: context7
description: Fetch up-to-date library, framework, and SDK documentation via Context7's search and docs endpoints. Use when the user asks about a library/API (React, Next.js, Prisma, Supabase, Tailwind, Django, Vue, etc.) and you need current docs, not Claude's training-time knowledge. Skip this skill for generic programming questions that don't require library-specific docs.
license: MIT (skill wrapper; Context7 API terms apply)
---

# Context7

Live documentation lookup for libraries, frameworks, and SDKs. Operates Context7 via its public REST API — no MCP server required.

**Use this instead of training memory whenever the answer depends on the library's *current* behavior** (current major version, recent API changes, new methods, deprecations). Training data goes stale fast for active libraries.

## When to use vs. skip

| Use Context7                                              | Skip Context7                                                |
| --------------------------------------------------------- | ------------------------------------------------------------ |
| "How do I do X in Next.js 15 / React 19 / Prisma 6?"      | "What's a closure in JavaScript?" (language concept)         |
| "What's the right way to set up Auth.js v5 middleware?"   | "Fix this TypeError in my code" (debugging user's own code)  |
| "Did the Supabase client API change for storage uploads?" | "Convert this loop to a map" (pure refactor, no SDK)         |
| Anything where you'd otherwise hedge with "as of my training cutoff…" | Std-lib (`fs`, `os`, `collections`) unless asking about a recent runtime version |

If you catch yourself about to write code from memory for a library that's released in the last 18 months, stop and call this skill first.

## Credentials check

```bash
[ -n "$CONTEXT7_API_KEY" ] && echo "CONTEXT7_API_KEY: PRESENT" || echo "CONTEXT7_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would land in the conversation transcript.

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
- All requests are GET. Responses are markdown by default (`type=txt`) or JSON (`type=json`).

## Two-step workflow

Docs lookup is two calls: (1) **resolve** the library name to its canonical `libraryId`, (2) **fetch** docs for that ID, scoped by topic.

### Step 1 — Resolve library name → library ID

```bash
curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/search?query=next.js"
```

Returns an array of matches. For each candidate, weigh:

- **Name match** — does it actually correspond to what the user asked? "next.js auth" returns *both* `/vercel/next.js` and `/nextauthjs/next-auth`. Different libraries.
- **Trust / popularity signal** — when present in the result (`trustScore`, `totalSnippets`, stars), prefer high values. Low-trust forks usually mean unofficial mirrors.
- **`lastUpdate` recency** — abandoned mirrors with stale docs are worse than the canonical repo.
- **Maintainer org** — `/vercel/next.js` (official) beats `/some-fork/next.js-clone`.

**When uncertain between 2–3 close matches, do NOT guess.** Show the top candidates to the user with a one-line description each and ask which one they want. A wrong libraryId silently returns wrong docs — that's worse than no docs.

### Step 2 — Fetch docs for the library

```bash
curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/vercel/next.js?topic=app-router&tokens=5000"
```

**Path:**
- `{libraryId}` is appended verbatim. Pass `/vercel/next.js` as-is — **do NOT URL-encode the leading slash** (would become `%2Fvercel%2Fnext.js` and 404).

**Query params:**

| Param    | Default | Use                                                                                          |
| -------- | ------- | -------------------------------------------------------------------------------------------- |
| `topic`  | none    | Single keyword that filters the docs to a slice. Almost always set this — see sizing below.  |
| `tokens` | 10000   | Cap on response size. Min 1000.                                                              |
| `type`   | `txt`   | `txt` returns markdown (default, best for reading). `json` returns structured snippet array. |

### Topic + token sizing — pick deliberately

| Question shape                                       | `topic`                  | `tokens` |
| ---------------------------------------------------- | ------------------------ | -------- |
| Quick API check: "is `useFormState` still a thing?"  | `forms` or `hooks`       | 2000–3000 |
| How-to: "how do I set up middleware auth?"           | `middleware-auth`        | 4000–5000 |
| Migration / deep dive: "what changed v4 → v5?"       | `migration` or `v5`      | 8000–10000 |
| Browsing: "what does this library even do?"          | omit                     | 5000      |

A full docs dump without `topic` is almost never what you want — it wastes tokens and dilutes signal.

## Common patterns

```bash
# Resolve + fetch in one go for a common library
LIB_ID=$(curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/search?query=auth.js" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['results'][0]['libraryId'])")

curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1${LIB_ID}?topic=nextjs-setup&tokens=5000"

# Skip search if you're 100% sure of the canonical ID (well-known orgs)
curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/vercel/next.js?topic=app-router&tokens=5000"

# Multi-library question: resolve + fetch each, then synthesize.
# Run them in parallel via & for speed.
curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/vercel/next.js?topic=middleware&tokens=4000" > /tmp/next.md &
curl -sL -H "Authorization: Bearer $CONTEXT7_API_KEY" \
  "https://context7.com/api/v1/nextauthjs/next-auth?topic=v5-middleware&tokens=4000" > /tmp/auth.md &
wait
```

## Gotchas

- **Wrong library wins silently.** A bad pick at step 1 returns docs that *look* authoritative for the wrong project. Always sanity-check that the response opens with the library you expected.
- **Don't paraphrase from training memory.** The whole reason to call Context7 is freshness — quote / adapt from the returned docs, and if the response contradicts what you "remember", trust the response.
- **404 on a fetch usually means a typo in `libraryId` or URL-encoded slash.** Re-check the path is `/{org}/{repo}` literal.
- **Library not in catalog** — search returns no matches → fall back to web search and tell the user Context7 didn't have it. Don't fabricate a libraryId.
- **`tokens` < 1000 is rejected.** Use 2000 as the practical floor.
- **`topic` is a free-text filter, not an enum.** Phrase it like a section title in the docs (`server-actions`, `migration-v5`, `middleware-auth`). Multi-word topics use hyphens.
- **Response is markdown with code fences.** When piping into another tool, prefer `type=json` to avoid re-parsing the markdown structure.
- **Rate limits** — free tier is generous for `/v1/{libraryId}` fetches and lighter for `/search`. Batch your search calls; don't loop.

## Attribution

When done, state: `Used skill: Context7 (from teleport catalog).`
