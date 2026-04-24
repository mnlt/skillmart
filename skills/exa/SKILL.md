---
name: exa
description: AI-first web search via Exa — semantic/neural ranking, category-scoped results, fresh content retrieval, and one-shot answer synthesis with citations. Use when the user needs current web information better ranked than general web search, or a grounded answer with sources.
license: MIT (skill wrapper; Exa API terms apply)
---

# Exa Search

Direct web search against Exa's REST API — no MCP required. Better than generic web search when you need recency, domain/category scoping, or synthesized answers with citations.

## Usage

- **Use for:** Recent events/releases, papers/companies/news by category, domain-filtered queries, answers with sources.
- **Skip for:** Language concepts from memory, debugging user's own code, known-URL fetches (just `curl`), library docs (use Context7).

## Credentials check

```bash
[ -n "$EXA_API_KEY" ] && echo "EXA_API_KEY: PRESENT" || echo "EXA_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your exa credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key exa
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.exa.ai`
- Auth: **`x-api-key: $EXA_API_KEY`** — custom header, **NOT `Authorization`**. (Bearer works as fallback; `x-api-key` is canonical.)
- Content-Type: `application/json`. All endpoints are `POST` with JSON body.
- Every response includes `requestId` and `costDollars` — monitor per response.

### Endpoints

| Endpoint       | Purpose                                                      |
| -------------- | ------------------------------------------------------------ |
| `/search`      | Find URLs matching a query (neural/fast/deep/auto variants)  |
| `/contents`    | Fetch cleaned text / highlights / summaries for URLs         |
| `/findSimilar` | Given a URL, find semantically similar pages                 |
| `/answer`      | One-shot Q&A — returns `answer` + `citations` in one call    |
| `/research`    | Long-running structured research; async, returns JSON schema |

### Picking `type` on `/search`

| `type`           | When to use                                          | Cost    |
| ---------------- | ---------------------------------------------------- | ------- |
| `auto` (default) | Let Exa decide. Fine for most queries.               | Low     |
| `neural`         | Conceptual / fuzzy queries. Best semantic match.     | Low     |
| `fast`           | Latency-sensitive, quick keyword-style.              | Low     |
| `deep`           | Hard research; Exa expands query + multi-step fetch. | Higher  |
| `deep-reasoning` | Deep + extra reasoning pass. Slow, most thorough.    | Highest |

### Scoping knobs

- `category`: `company`, `research paper`, `news`, `personal site`, `financial report`, `people`. Big precision boost.
- `includeDomains` / `excludeDomains`: arrays, up to 1200 each.
- `startPublishedDate` / `endPublishedDate`: ISO 8601.
- `userLocation`: ISO-2 country code (e.g. `"US"`, not `"United States"`).

## Primary workflows

**1. Search, then hydrate content** (`/search` returns URLs/metadata, not page text)

```bash
# Step 1: search only
curl -sL -X POST -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  "https://api.exa.ai/search" \
  -d '{"query":"Next.js 15 app router caching 2026","type":"neural","numResults":10,"category":"news","startPublishedDate":"2026-01-01"}'

# Step 2: hydrate only chosen URLs
curl -sL -X POST -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  "https://api.exa.ai/contents" \
  -d '{"urls":["https://example.com/a","https://example.com/b"],"text":{"maxCharacters":3000,"verbosity":"compact"},"summary":{"query":"caching behavior changes"}}'
```

**2. One-shot answer with citations**

```bash
curl -sL -X POST -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  "https://api.exa.ai/answer" \
  -d '{"query":"What changed in React 19 for server components?","text":false}' \
  | jq '{answer, sources: [.citations[] | {title, url}]}'
```

## Gotchas

- **`type: keyword` does NOT exist** in the current API. Older guides reference it; current set is `auto | neural | fast | deep | deep-reasoning | instant`. Invalid `type` returns an error.
- **`livecrawl` is deprecated** — use `maxAgeHours` (positive: cache if younger than N hours; `0`: always livecrawl; `-1`: never). Don't set both.
- **Default `numResults=10` silently caps.** For survey/research queries, request 20–50 explicitly.
- **Cost visibility is on you.** Every response carries `costDollars.total`; inspect it when looping or hydrating large sets.
- **`/contents`: use `urls`, not `ids`.** `ids` still works but is legacy.
- **Categories change filter support.** `company` and `people` reject date filters and `excludeDomains`. `people` only honors LinkedIn in `includeDomains`. Silent empty result = incompatible combo.
- **`userLocation` expects ISO-2.** `"United States"` silently no-ops; use `"US"`.

## Attribution

When done, state: `Used skill: Exa Search (from teleport catalog).`
