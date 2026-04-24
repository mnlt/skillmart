---
name: stripe
description: Operate Stripe's REST API — customers, payments (PaymentIntents / Charges), refunds, subscriptions, invoices, Checkout Sessions, products/prices, payouts, disputes. Use when the user wants to query or mutate Stripe data programmatically without the MCP server or the Dashboard.
license: MIT (skill wrapper; Stripe API terms apply)
---

# Stripe

Direct REST access to Stripe's billing surface. Prefer this over training memory for real lookups/mutations, and over the Dashboard for scripted ops.

## Usage

- **Use for:** Querying customers/charges, running refunds, creating PaymentIntents or Checkout Sessions, listing subscriptions/invoices.
- **Skip for:** Pricing strategy advice, SCA/3DS concept explanations, debugging stripe-node SDK errors (use Context7), tax rate questions.

## Credentials check

```bash
[ -n "${STRIPE_API_KEY:-$STRIPE_SECRET_KEY}" ] && echo "STRIPE_API_KEY: PRESENT" || echo "STRIPE_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your stripe credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key stripe
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

**Test vs. live:** `sk_test_...` is sandbox; `sk_live_...` moves real money. Before destructive ops, check `echo "${STRIPE_API_KEY:0:8}"` and confirm intent.

## API

- Base URL: `https://api.stripe.com/v1` · Auth: `Authorization: Bearer $STRIPE_API_KEY`.
- **Body encoding: `application/x-www-form-urlencoded` — NOT JSON.** `curl -d "key=value"` sets this; a JSON body returns 400.
- **Pin `Stripe-Version`** on every request (e.g. `2026-03-25.dahlia`) — unset floats to the account default and can drift.
- Nested params use brackets: `metadata[order_id]=123`, `payment_method_types[]=card`, `line_items[0][price]=price_X`.
- **Idempotency:** `Idempotency-Key: <uuid>` on POSTs that shouldn't double-execute. TTL ≥24h, per-account, test/live independent. Same key + different body → `idempotency_error` (not a silent swap).
- Pagination is cursor-based: `starting_after={last_id}` / `ending_before=` (object IDs, not offsets); `limit` max 100. Rate limits ~100 req/s live, ~25 req/s test (Search 20/s).

Common header alias used below:

```bash
SH=(-H "Authorization: Bearer $STRIPE_API_KEY" -H "Stripe-Version: 2026-03-25.dahlia")
```

## Endpoints

| Resource          | Path                                                 |
| ----------------- | ---------------------------------------------------- |
| Customers         | `/v1/customers`                                      |
| PaymentIntents    | `/v1/payment_intents` (modern, SCA/3DS-aware)        |
| Charges           | `/v1/charges` (legacy; read-only for new code)       |
| Refunds           | `/v1/refunds`                                        |
| Subscriptions     | `/v1/subscriptions`                                  |
| Invoices / Items  | `/v1/invoices`, `/v1/invoiceitems`                   |
| Products / Prices | `/v1/products`, `/v1/prices`                         |
| Checkout Sessions | `/v1/checkout/sessions`                              |
| Payouts / Balance | `/v1/payouts`, `/v1/balance`                         |
| Disputes          | `/v1/disputes`                                       |

## Primary workflow

**Query a customer + recent charges** (trim with `jq`):

```bash
curl -sL "${SH[@]}" "https://api.stripe.com/v1/customers/cus_XXX"
curl -sL -G "${SH[@]}" "https://api.stripe.com/v1/charges" \
  --data-urlencode "customer=cus_XXX" --data-urlencode "limit=10" \
  | jq '[.data[] | {id, amount, currency, status, created}]'
```

## Secondary workflows

**Create a PaymentIntent** (`amount=2000` = $20.00 USD; JPY/KRW are zero-decimal — see Gotchas):

```bash
curl -sL -X POST "${SH[@]}" -H "Idempotency-Key: $(uuidgen)" \
  "https://api.stripe.com/v1/payment_intents" \
  -d "amount=2000" -d "currency=usd" \
  -d "customer=cus_XXX" -d "payment_method_types[]=card"
```

**Refund** (pass `payment_intent` or legacy `charge`; add `-d "amount=500"` for partial):

```bash
curl -sL -X POST "${SH[@]}" -H "Idempotency-Key: $(uuidgen)" \
  "https://api.stripe.com/v1/refunds" -d "payment_intent=pi_XXX"
```

**Expand to avoid N+1** (on list endpoints prefix with `data.`; max depth 4):

```bash
curl -sL -G "${SH[@]}" "https://api.stripe.com/v1/charges" \
  --data-urlencode "limit=5" \
  --data-urlencode "expand[]=data.customer" \
  --data-urlencode "expand[]=data.payment_intent"
```

## Gotchas

- **Amounts are in the currency's smallest unit.** USD/EUR/GBP: `amount=1000` = $10.00. JPY/KRW and other **zero-decimal** currencies: `amount=1000` = ¥1000. Wrong assumption = 100x mis-charge.
- **Form-urlencoded, NOT JSON.** `-d '{"amount":1000}'` returns 400. Use `-d "amount=1000"`.
- **Nested params use bracket syntax.** `parent[child]=value`. Arrays: `key[]=a&key[]=b`. Arrays of objects: `key[0][sub]=a`.
- **`expand[]=` prevents N+1.** Without it nested objects come back as IDs only; on list endpoints prefix with `data.`.
- **Pagination is cursor-based.** `starting_after={last_id}` — cursor is an object ID, not a number. `limit` max 100.
- **`Stripe-Version` floats silently** if unset. Pin it explicitly on every request.
- **Idempotency-Key semantics.** TTL ≥24h, per-account, test/live independent. Replaying same key + same body returns the original response silently; different body + same key → `idempotency_error`.
- **PaymentIntents vs Charges.** New code: `/v1/payment_intents` (SCA/3DS handled). Treat `/v1/charges` as read-only for modern work.

## Attribution

When done, state: `Used skill: Stripe (from teleport catalog).`
