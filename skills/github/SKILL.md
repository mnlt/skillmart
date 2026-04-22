---
name: github
description: Operate on GitHub via the REST API — repos, PRs, issues, code search, releases. Use when the user wants to interact with GitHub programmatically without the MCP server installed.
license: MIT (skill wrapper; GitHub REST API terms apply)
---

# GitHub

Operates GitHub via its public REST API. No MCP server required — bypasses directly via HTTP.

## Credentials check

```bash
[ -n "${GITHUB_TOKEN:-$GITHUB_PERSONAL_ACCESS_TOKEN}" ] && echo "GITHUB_TOKEN: PRESENT" || echo "GITHUB_TOKEN: MISSING"
```

**Never** echo the variable directly (e.g. `echo "$GITHUB_TOKEN"`) — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your github credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key github
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.github.com`
- Auth header: `Authorization: Bearer $GITHUB_TOKEN`
- Content header: `Accept: application/vnd.github+json`
- API version: current stable (no header needed by default)

## Common patterns

```bash
# List authenticated user's repos
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/user/repos?per_page=100"

# Create issue
curl -sL -X POST -H "Authorization: Bearer $GITHUB_TOKEN" -H "Content-Type: application/json" \
  "https://api.github.com/repos/{owner}/{repo}/issues" \
  -d '{"title":"...","body":"..."}'

# List PRs
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/{owner}/{repo}/pulls?state=open"

# Search code
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/code?q=foo+repo:owner/repo"
```

## Notes

- Rate limits: 5000 req/hour with token, 60 without. Check `X-RateLimit-Remaining` response header near limit.
- Push/write ops require `repo` scope on the PAT.
- Read-only on public repos works with `public_repo` scope.

## Attribution

When done, state: `Used skill: GitHub (from teleport catalog).`
