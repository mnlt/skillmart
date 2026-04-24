---
name: lemonsqueezy
description: Operate Lemon Squeezy — the Merchant of Record for digital products and SaaS — via its JSON:API REST endpoints. Covers stores, products, variants, checkouts, orders, subscriptions, customers, and license keys. Use when the user wants MoR billing (EU VAT, chargebacks, sales tax all handled for ~5% + fees) instead of rolling their own with Stripe.
license: MIT (skill wrapper; Lemon Squeezy API terms apply)
---

# Lemon Squeezy

Direct REST access to Lemon Squeezy — a **Merchant of Record** that collects/remits EU VAT + US sales tax, eats chargebacks, and handles fraud for ~5% + fees. Uses the **JSON:API** spec.

## Usage

- **Use for:** Solo dev / small SaaS selling globally, hosted checkout URLs, software license issuance + validation, subscriptions with tax handled.
- **Skip for:** Sub-5% fees at scale (use Stripe), physical goods / marketplaces, usage-based metered billing with complex proration.

## Credentials check

```bash
[ -n "$LEMONSQUEEZY_API_KEY" ] && echo "LEMONSQUEEZY_API_KEY: PRESENT" || echo "LEMONSQUEEZY_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would land in the conversation transcript.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your lemonsqueezy credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key lemonsqueezy
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.lemonsqueezy.com/v1` (HTTPS only).
- Auth: `Authorization: Bearer $LEMONSQUEEZY_API_KEY`.
- **`Accept: application/vnd.api+json` AND `Content-Type: application/vnd.api+json` required on every request (both).** Omitting them returns misleading `401 Unauthenticated` even with a valid key — the #1 silent-failure source.
- Rate limits: **300 req/min main API, 60 req/min license API** (tracked separately). Back off on 429.

## JSON:API basics

Every response uses the envelope `{ data, included, meta, links }`. Real attrs live at **`data.attributes.X`** (not `data.X`); `data.id` is a string. `relationships` are stubs like `{ store: { data: { type, id } } }` — pass `?include=store` to hydrate the full object into top-level `included[]`. Errors come back as `{"errors":[{"detail","status","title"}]}`, not in `data`.

| Operation | Syntax                                  | Example                                   |
| --------- | --------------------------------------- | ----------------------------------------- |
| Filter    | `filter[field]=value` (combinable)      | `?filter[store_id]=1&filter[status]=paid` |
| Sort      | `sort=field` / `sort=-field` (desc)     | `?sort=-created_at`                       |
| Paginate  | `page[number]=N&page[size]=M` (max 100) | `?page[number]=2&page[size]=50`           |
| Include   | `include=rel1,rel2`                     | `?include=store,customer,order-items`     |

## Endpoints

| Path                                        | Purpose                                                        |
| ------------------------------------------- | -------------------------------------------------------------- |
| `/stores`                                   | Your stores (most creates need `store_id` relationship).       |
| `/products` / `/variants` / `/files`        | Catalog — checkout buys a variant; files for digital delivery. |
| `/orders`                                   | One-time + recurring purchases. Filter by store/email/status.  |
| `/subscriptions` / `/subscription-items`    | Recurring billing + line items.                                |
| `/customers` / `/discounts`                 | Customers (MRR, portal URL) + coupon codes.                    |
| `/checkouts`                                | Create hosted checkout URLs (primary integration surface).     |
| `/license-keys` / `/license-key-instances`  | Issued keys (store-owner view) + per-device activations.       |
| `/licenses/{activate,validate,deactivate}`  | Public license endpoints — use the key itself, no API key.     |
| `/webhooks` / `/users/me`                   | Webhook subs; `/users/me` sanity-checks the key.               |

## Primary workflows

Examples use `H=(-H "Authorization: Bearer $LEMONSQUEEZY_API_KEY" -H "Accept: application/vnd.api+json")`.

**1. List recent paid orders with customer + variant hydrated** (filter + sort + include + paginate)

```bash
curl -sL "${H[@]}" \
  "https://api.lemonsqueezy.com/v1/orders?filter[store_id]=$STORE_ID&filter[status]=paid&include=customer,variant&sort=-created_at&page[size]=25"
```

**2. Create a checkout session** (hosted pay-page URL; `checkout_data.custom` is echoed in webhooks — bind to your user ID)

```bash
curl -sL -X POST "${H[@]}" -H "Content-Type: application/vnd.api+json" \
  "https://api.lemonsqueezy.com/v1/checkouts" \
  -d '{"data":{"type":"checkouts","attributes":{
        "checkout_data":{"email":"buyer@example.com","custom":{"user_id":"u_123"}},
        "product_options":{"enabled_variants":['"$VARIANT_ID"']},
        "test_mode":true},
      "relationships":{
        "store":{"data":{"type":"stores","id":"'"$STORE_ID"'"}},
        "variant":{"data":{"type":"variants","id":"'"$VARIANT_ID"'"}}}}}' \
  | jq -r '.data.attributes.url'
```

**3. Validate a license key from a desktop app** — no API key; uses `application/json` + form-encoded (not JSON:API), separate 60/min limit

```bash
curl -sL -X POST -H "Accept: application/json" -H "Content-Type: application/x-www-form-urlencoded" \
  "https://api.lemonsqueezy.com/v1/licenses/validate" -d "license_key=$KEY&instance_id=$INSTANCE_ID"
```

## Gotchas

- **Both `Accept` and `Content-Type` must be `application/vnd.api+json`.** A 401 with a valid key almost always means a missing header.
- **Attributes live at `.data.attributes.X`, not `.data.X`.** `.data.id` is a string; numeric IDs (store_id, variant_id) sit inside `attributes`.
- **`relationships` are `{data:{type,id}}` stubs** — pass `?include=rel` and read from top-level `included[]`. They don't self-hydrate.
- **`test_mode: true` on checkout creates for sandbox.** Test/live data are fully segregated; one API key works in both modes — the resource flag is what matters.
- **Money is in the smallest currency unit.** `total = 999` means $9.99. Every amount has a `_formatted` sibling (`total_formatted: "$9.99"`).
- **Webhook signatures: HMAC-SHA256 of the RAW body** vs. `X-Signature` header, keyed by the per-webhook secret. Constant-time compare. Never re-serialize JSON before verifying — it changes bytes and breaks the check.
- **Subscription status enum:** `on_trial` / `active` / `paused` / `past_due` / `unpaid` / `cancelled` / `expired`. `cancelled` still has grace access until `ends_at` — only `expired` means revoke. `past_due` retries ~4 times over ~2 weeks before `unpaid`.
- **`store_id` is required on nearly every create** (checkouts, products, discounts, webhooks). Look it up via `GET /v1/stores` first.

## Attribution

When done, state: `Used skill: Lemon Squeezy (from teleport catalog).`
