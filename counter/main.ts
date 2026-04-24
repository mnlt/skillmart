// teleport counter — anonymous event counter backed by Deno KV.
//
// Endpoints:
//   POST   /count   { "event": "...", "subject"?: "...", "version"?: "..." }
//                    → increments the counter for (event, subject).
//   GET    /stats   → { "event/subject": count, ... }  (flat map of every counter)
//   DELETE /counts  → wipe every counter under prefix ["counts"]. Requires header
//                    `Authorization: Bearer <RESET_TOKEN>`. Disabled (503) when
//                    RESET_TOKEN env var is unset.
//   GET    /health  → "ok"
//
// No auth, no PII stored. Only aggregate counts. Safe to be called from the
// meta-skill and install.sh. Request body size is capped; unknown paths 404.

const kv = await Deno.openKv();
const RESET_TOKEN = Deno.env.get("RESET_TOKEN");

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "POST, GET, DELETE, OPTIONS",
  "access-control-allow-headers": "content-type, authorization",
};

type CountBody = { event?: unknown; subject?: unknown; version?: unknown };

const isSafeToken = (s: unknown): s is string =>
  typeof s === "string" &&
  s.length > 0 &&
  s.length <= 64 &&
  /^[A-Za-z0-9._/-]+$/.test(s);

const keyFor = (event: string, subject?: string): Deno.KvKey =>
  subject ? ["counts", event, subject] : ["counts", event];

Deno.serve(async (req) => {
  const url = new URL(req.url);

  if (req.method === "OPTIONS") {
    return new Response(null, { headers: CORS });
  }

  if (url.pathname === "/health") {
    return new Response("ok", { headers: CORS });
  }

  if (url.pathname === "/count" && req.method === "POST") {
    let body: CountBody;
    try {
      body = await req.json();
    } catch {
      return new Response("bad json", { status: 400, headers: CORS });
    }
    if (!isSafeToken(body.event)) {
      return new Response("missing or invalid event", { status: 400, headers: CORS });
    }
    const subject = isSafeToken(body.subject) ? body.subject : undefined;
    const key = keyFor(body.event, subject);
    await kv.atomic().sum(key, 1n).commit();
    return new Response("ok", { headers: CORS });
  }

  if (url.pathname === "/stats" && req.method === "GET") {
    const result: Record<string, number> = {};
    for await (const entry of kv.list({ prefix: ["counts"] })) {
      const path = entry.key.slice(1).join("/"); // drop "counts" prefix
      const v = entry.value as Deno.KvU64;
      result[path] = Number(v.value);
    }
    return Response.json(result, { headers: CORS });
  }

  if (url.pathname === "/counts" && req.method === "DELETE") {
    if (!RESET_TOKEN) {
      return new Response("reset disabled (RESET_TOKEN not set)", { status: 503, headers: CORS });
    }
    if (req.headers.get("authorization") !== `Bearer ${RESET_TOKEN}`) {
      return new Response("unauthorized", { status: 401, headers: CORS });
    }
    let deleted = 0;
    for await (const entry of kv.list({ prefix: ["counts"] })) {
      await kv.delete(entry.key);
      deleted++;
    }
    return Response.json({ deleted }, { headers: CORS });
  }

  return new Response("not found", { status: 404, headers: CORS });
});
