---
name: github
description: Operate on GitHub via the REST API — repos, PRs, issues, code search, actions, releases. Use when the user wants scripted / cross-repo operations, doesn't have `gh` installed, or needs behavior the `gh` CLI doesn't expose cleanly.
license: MIT (skill wrapper; GitHub REST API terms apply)
---

# GitHub

Direct REST access to GitHub — repos, PRs, issues, code search, Actions, releases. Use when the answer depends on *current* state and `gh` is absent or too narrow.

## Usage

- **Use for:** Cross-repo fan-out, scripted PR/issue operations, code search piped to `jq`, CI status reads, when `gh` isn't installed.
- **Skip for:** Local edits (filesystem), commits/pushes (`git`), one-shot reads when user has `gh` (`gh pr view`), concept questions.

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
- Auth: `Authorization: Bearer $GITHUB_TOKEN`
- Accept: `Accept: application/vnd.github+json` (recommended on every call for stable response shape).
- Version: `X-GitHub-Api-Version: 2022-11-28` — **pin this header** or the default floats to whatever GitHub promotes next.
- Rate limits: **5000 req/hr** authenticated (60 unauth); Search is a separate **30 req/min** bucket. Watch `x-ratelimit-*`.
- Pagination: `per_page` (max **100**), `page` 1-indexed. Follow the `Link` response header (`rel="next"`) — not offset math.

## Token flavors

Fine-grained PAT (preferred: per-repo, named permissions like `contents:read`) vs classic PAT (coarse scopes like `repo`, `workflow`). Inside Actions, `GITHUB_TOKEN` is workflow-scoped. **Scopes matter:** a token missing the required scope returns **404, not 401** (see Gotchas).

Samples below use a helper that bundles the three standard headers:

```bash
GH() { curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "$@"; }
```

## Endpoints

| Area           | Path                                                                |
| -------------- | ------------------------------------------------------------------- |
| Repo metadata  | `GET /repos/{owner}/{repo}` (read `.default_branch`)                |
| Contents       | `GET /repos/{owner}/{repo}/contents/{path}?ref={sha}` (base64)      |
| Issues         | `GET/POST /repos/{owner}/{repo}/issues` (returns PRs too)           |
| Issue comments | `POST /repos/{owner}/{repo}/issues/{n}/comments`                    |
| Pulls          | `GET /repos/{owner}/{repo}/pulls` · `GET .../pulls/{n}` (diff via Accept) |
| PR reviews     | `POST /repos/{owner}/{repo}/pulls/{n}/reviews` (`APPROVE`/`REQUEST_CHANGES`/`COMMENT`) |
| Search         | `GET /search/code` · `/search/issues` · `/search/repositories`      |
| Actions        | `GET /repos/{owner}/{repo}/actions/runs`                            |
| Releases       | `GET /repos/{owner}/{repo}/releases/latest`                         |

## Primary workflows

**1. Issue triage (list + comment)**

```bash
GH "https://api.github.com/repos/OWNER/REPO/issues?state=open&labels=bug&sort=updated&per_page=50"
GH -X POST "https://api.github.com/repos/OWNER/REPO/issues/NUM/comments" \
  -d '{"body":"Thanks — reproduced on main, PR incoming."}'
```

**2. PR review (list + diff + review)**

```bash
GH "https://api.github.com/repos/OWNER/REPO/pulls?state=open&sort=updated"
# Unified diff: swap Accept on the same endpoint
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github.diff" \
  "https://api.github.com/repos/OWNER/REPO/pulls/NUM"
GH -X POST "https://api.github.com/repos/OWNER/REPO/pulls/NUM/reviews" \
  -d '{"event":"APPROVE","body":"LGTM, tests cover the edge case."}'
```

**3. Code search (trim with `jq`)**

```bash
# Qualifiers: repo:, language:, path:, user:, org:, in:file, extension:
GH "https://api.github.com/search/code?q=useState+repo:facebook/react+language:typescript&per_page=30" \
  | jq '[.items[] | {repo: .repository.full_name, path, url: .html_url}]'
```

## Gotchas

- **Missing `X-GitHub-Api-Version` floats to the current default** — breaks silently over time when GitHub ships a new version. Pin it.
- **Token-scope errors return 404, not 401/403.** A classic PAT missing `repo` sees private repos as "not found." If `GET /repos/{owner}/{repo}` 404s on a repo you know exists, suspect scopes before spelling.
- **Secondary rate limits / abuse detection hit before the hourly cap.** Parallel bursts against the same resource return `403` with `x-ratelimit-remaining` still positive. Throttle and retry with backoff.
- **Search API is a separate 30 req/min bucket** and caps total results at **1000 per query** — pagination beyond **page 10** errors out. Refine the query instead of paging.
- **`/issues` returns pull requests too** (every PR is an issue in GitHub's model). Filter `.pull_request == null` when you want pure issues.
- **Default branch isn't always `main`.** Read `.default_branch` from `GET /repos/{owner}/{repo}` before building any `ref=` URL.
- **`Link` header is authoritative for pagination**, not offset math. Missing `rel="next"` = done.

## Attribution

When done, state: `Used skill: GitHub (from teleport catalog).`
