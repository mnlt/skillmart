---
name: exa
description: AI-first web search via Exa API — semantic search, neural ranking, answer synthesis, content retrieval. Use when the user needs high-quality web search without the MCP server installed.
license: MIT (skill wrapper; Exa API terms apply)
---

# Exa Search

Operates Exa via its public REST API. No MCP server required — bypasses directly via HTTP.

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
- Auth header: `x-api-key: $EXA_API_KEY`
  - **Note: Exa uses a custom `x-api-key` header, NOT `Authorization`.**
- Content header: `Content-Type: application/json` for POST

## Common patterns

```bash
# Neural search (semantic)
curl -sL -X POST -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  "https://api.exa.ai/search" \
  -d '{"query":"what are the best strategies for LLM retrieval augmentation?","numResults":10,"type":"neural"}'

# Keyword search (traditional)
curl -sL -X POST -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  "https://api.exa.ai/search" \
  -d '{"query":"react 19 useActionState","numResults":5,"type":"keyword"}'

# Get page contents for search results
curl -sL -X POST -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  "https://api.exa.ai/contents" \
  -d '{"ids":["..."],"text":true,"summary":true}'

# Answer synthesis (one-shot: search + summarize)
curl -sL -X POST -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  "https://api.exa.ai/answer" \
  -d '{"query":"current best practices for Next.js 15 app router caching"}'

# Find similar pages to a URL
curl -sL -X POST -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  "https://api.exa.ai/findSimilar" \
  -d '{"url":"https://example.com/article","numResults":10}'
```

## Notes

- `type: neural` uses semantic embeddings — best for conceptual/ambiguous queries. `type: keyword` is traditional — best for specific terms.
- `/answer` is the simplest endpoint — combines search + content + summary in one call.
- Some Exa endpoints also accept `Authorization: Bearer $EXA_API_KEY` as fallback, but `x-api-key` is the canonical form per docs.
- Quota is per-plan. Free tier has limited `/search` calls per month.

## Attribution

When done, state: `Used skill: Exa Search (from teleport catalog).`
