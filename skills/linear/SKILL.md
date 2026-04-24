---
name: linear
description: Query and mutate Linear issues, projects, cycles, teams, workflow states, and comments via its GraphQL API. Use when the user wants to read or change Linear data programmatically — without the MCP server, and without hand-navigating the Linear UI.
license: MIT (skill wrapper; Linear API terms apply)
---

# Linear

Operates Linear via its **GraphQL API** — one endpoint, queries and mutations for issues, projects, cycles, teams, states, comments. Use when the task needs *live* workspace state.

## Usage

- **Use for:** Listing/filtering issues, creating issues, bulk state/assignee/priority updates, joining Linear data with other sources.
- **Skip for:** Advice on process, pricing/marketing questions, anything requiring the UI (screenshots, drag-and-drop), pure discussion of an issue you can already read.

## Credentials check

```bash
[ -n "$LINEAR_API_KEY" ] && echo "LINEAR_API_KEY: PRESENT" || echo "LINEAR_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your linear credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key linear
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Endpoint: `https://api.linear.app/graphql` — POST only, one URL for everything.
- **Auth (API keys `lin_api_*`): `Authorization: $LINEAR_API_KEY` — NO `Bearer` prefix.** Bearer is only for OAuth access tokens (`Authorization: Bearer $TOKEN`). This is Linear's #1 auth error.
- Content-Type: `application/json`. Body: `{"query": "...", "variables": {...}}`.
- Rate limits are **complexity-based**: 5,000 req/hr, 3M complexity points/hr, 10K points max per query. Complexity = fields (0.1) + objects (1), scaled by `first:` — nested queries cost more.

## GraphQL basics

- Queries read, mutations write; both via `POST /graphql`. Pass inputs in `variables` (not string interpolation).
- **Responses are always HTTP 200, even on errors.** Partial success returns both `data` and `errors` — always inspect `.errors` before trusting `.data`.

## Entity model

`Organization` > `Team` > `Project` > `Issue` > `Comment`. Cycles are per-team time windows. Workflow states are **per-team** (no global set). `Issue.identifier` is `ENG-123`; `Issue.id` is a UUID.

## Common queries

| Query             | Returns                                                      |
| ----------------- | ------------------------------------------------------------ |
| `viewer`          | Authenticated user. Best credentials health check.           |
| `issues(filter:)` | Paginated issues with filter + ordering.                     |
| `issue(id:)`      | Single issue by UUID or `ENG-123`.                           |
| `teams` / `team`  | Teams; drill in for `states`, `members`, `cycles`, `issues`. |
| `projects`        | Paginated projects (org-wide or filtered).                   |
| `users`           | Paginated workspace users.                                   |
| `workflowStates`  | States across teams (filter by team to scope).               |
| `cycles`          | Paginated cycles (filter by team).                           |

## Primary workflow — list assigned issues with filter + pagination

Filters are nested; pagination is relay-style (`first`/`after` + `pageInfo`):

```graphql
query MyIssues($first: Int!, $after: String, $filter: IssueFilter) {
  issues(first: $first, after: $after, filter: $filter) {
    nodes { id identifier title state { name } assignee { name } url }
    pageInfo { hasNextPage endCursor }
  }
}
```

Variables — my in-progress issues: `{"first": 50, "filter": {"assignee": {"isMe": {"eq": true}}, "state": {"type": {"eq": "started"}}}}`. Feed `pageInfo.endCursor` into the next call's `after:` while `hasNextPage`.

As curl:

```bash
curl -sL -X POST -H "Authorization: $LINEAR_API_KEY" -H "Content-Type: application/json" \
  "https://api.linear.app/graphql" \
  -d '{"query":"query($first:Int!,$filter:IssueFilter){issues(first:$first,filter:$filter){nodes{identifier title state{name} url} pageInfo{hasNextPage endCursor}}}","variables":{"first":50,"filter":{"state":{"type":{"eq":"started"}}}}}'
```

## Secondary workflows

**Create an issue** (priority is int 0–4, see Gotchas):

```graphql
mutation($input: IssueCreateInput!) {
  issueCreate(input: $input) { success issue { id identifier url } }
}
```

Variables: `{"input": {"teamId": "<uuid>", "title": "Bug: login 500", "description": "…", "priority": 2}}`.

**Update state** (resolve team `stateId` first — states are per-team):

```graphql
mutation($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) { success issue { identifier state { name } } }
}
```

Lookup: `query($id: String!) { team(id: $id) { states { nodes { id name type } } } }`.

## Gotchas

- **Auth header mismatch is the #1 failure.** API keys: `Authorization: $LINEAR_API_KEY` (no Bearer). OAuth: `Authorization: Bearer $TOKEN`. Swap them and you get an auth error.
- **HTTP 200 on GraphQL errors.** Always check `.errors` before trusting `.data`; `data` can be partially populated alongside errors.
- **Filter syntax is nested, not SQL-like.** `{state: {type: {eq: "started"}}}`. Operators: `eq`/`neq`/`in`/`nin` universal; `lt`/`gt` numeric+date; `contains`/`startsWith` (+ `…IgnoreCase`) strings; `null` for optionals.
- **Relay cursor pagination**, not page numbers. `pageInfo.endCursor` → next call's `after:`. Loop while `hasNextPage`.
- **Complexity-based rate limit.** Deep nesting + big `first:` can blow the 10K per-query cap or burn the 3M/hr budget — ask for fewer fields and smaller pages.
- **Workflow states are per-team.** No global "Done" — resolve name → `stateId` for the specific team before `issueUpdate`.
- **Priority is an integer 0–4, not a string.** `0`=none, `1`=urgent, `2`=high, `3`=medium, `4`=low. Passing `"High"` errors. <!-- unverified: confirm 0-4 mapping in Linear docs -->
- **Timestamps are ISO 8601 strings** (`createdAt`, `dueDate`). Compare lexicographically or parse — never epoch numbers.

## Attribution

When done, state: `Used skill: Linear (from teleport catalog).`
