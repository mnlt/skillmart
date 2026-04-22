#!/usr/bin/env python3
"""Measure real tool-schema token cost for top MCPs.

For each target MCP: spawn server (stdio via npx, or POST to hosted URL),
send JSON-RPC initialize + tools/list, grab the tool list, then call
Anthropic's count_tokens endpoint with those tools to get the real
Claude-tokenizer cost. Delta over a baseline no-tools call is the
net context overhead an MCP imposes at startup.

Writes results back into mcp-knowledge.json as:
  baseline_tokens_measured       (int, delta over baseline)
  baseline_tokens_measured_date  (YYYY-MM-DD)
  baseline_tokens_measured_tools (count)

Requires: ANTHROPIC_API_KEY in env. npx in PATH for stdio MCPs.
"""
import json, os, subprocess, sys, time, select, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "mcp-knowledge.json"
MODEL = "claude-haiku-4-5-20251001"

TOP10 = ["github", "notion", "slack", "linear", "stripe",
         "supabase", "figma", "jira", "sentry", "vercel"]

# Per-MCP launch overrides. MCPs often require specific CLI args and/or
# multiple env vars beyond what's in mcp-knowledge.json. For stdio MCPs,
# "args" is appended after "npx -y <pkg>". For hosted-only MCPs without
# a runnable stdio fallback, we note them with "skip_reason".
MCP_LAUNCH = {
    "github":   {"pkg": "@modelcontextprotocol/server-github", "env": {"GITHUB_TOKEN": "dummy"}},
    "notion":   {"pkg": "@notionhq/notion-mcp-server", "env": {"NOTION_API_KEY": "dummy"}},
    "slack":    {"pkg": "@modelcontextprotocol/server-slack",
                 "env": {"SLACK_BOT_TOKEN": "dummy", "SLACK_TEAM_ID": "dummy"}},
    "linear":   {"pkg": "@tacticlaunch/mcp-linear", "env": {"LINEAR_API_TOKEN": "dummy"}},
    "stripe":   {"pkg": "@stripe/mcp", "args": ["--tools=all", "--api-key=sk_test_dummy"]},
    "supabase": {"pkg": "@supabase/mcp-server-supabase", "args": ["--access-token=dummy"]},
    "figma":    {"pkg": "figma-developer-mcp", "args": ["--figma-api-key=dummy", "--stdio"]},
    "jira":     {"pkg": "jira-mcp", "env": {"JIRA_URL": "https://dummy.atlassian.net",
                                             "JIRA_EMAIL": "d@x.com", "JIRA_API_TOKEN": "dummy"}},
    "sentry":   {"hosted": "https://mcp.sentry.dev/mcp"},
    "vercel":   {"pkg": "@vercel/mcp-adapter", "env": {"VERCEL_TOKEN": "dummy"}},
}


def jsonrpc_line(msg):
    return (json.dumps(msg) + "\n").encode()


def read_response(proc, id_, timeout):
    start = time.time()
    buf = b""
    while time.time() - start < timeout:
        ready, _, _ = select.select([proc.stdout], [], [], 1.0)
        if not ready:
            if proc.poll() is not None:
                leftover = b""
                try:
                    leftover = os.read(proc.stdout.fileno(), 8192)
                except Exception:
                    pass
                tail = (buf + leftover).decode(errors="replace")[-500:]
                return None, f"process exited: {tail}"
            continue
        chunk = os.read(proc.stdout.fileno(), 8192)
        if not chunk:
            # EOF — process closed stdout
            tail = buf.decode(errors="replace")[-500:]
            return None, f"stdout closed (rc={proc.poll()}): {tail}"
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                resp = json.loads(line.decode())
            except json.JSONDecodeError:
                continue
            if resp.get("id") == id_:
                return resp, None
    return None, f"timeout after {timeout}s"


def measure_stdio(package, env_vars=None, extra_args=None, init_timeout=120, list_timeout=30):
    env = os.environ.copy()
    env["NODE_NO_WARNINGS"] = "1"
    if env_vars:
        env.update(env_vars)
    cmd = ["npx", "-y", package]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, env=env, bufsize=0,
    )
    try:
        proc.stdin.write(jsonrpc_line({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "teleport-measure", "version": "0.1"},
            }
        }))
        proc.stdin.flush()
        init, err = read_response(proc, 1, timeout=init_timeout)
        if not init:
            return None, err or "no initialize response"
        if "error" in init:
            return None, f"initialize error: {init['error']}"

        proc.stdin.write(jsonrpc_line({
            "jsonrpc": "2.0", "method": "notifications/initialized"
        }))
        proc.stdin.flush()

        proc.stdin.write(jsonrpc_line({
            "jsonrpc": "2.0", "id": 2, "method": "tools/list"
        }))
        proc.stdin.flush()
        tools, err = read_response(proc, 2, timeout=list_timeout)
        if not tools:
            return None, err or "no tools/list response"
        if "error" in tools:
            return None, f"tools/list error: {tools['error']}"
        return tools.get("result", {}).get("tools", []), None
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()


def measure_hosted(url, extra_headers=None, timeout=30):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "teleport-measure/0.1 (+https://github.com/mnlt/teleport)",
    }
    if extra_headers:
        headers.update(extra_headers)

    # Some hosted MCPs require a full initialize handshake even over HTTP.
    # First try a simple tools/list.
    def _post(payload):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode(), None
        except urllib.error.HTTPError as e:
            return None, f"HTTP {e.code}: {e.read().decode()[:200]}"
        except Exception as e:
            return None, str(e)

    def _parse_response(body, expected_id):
        # SSE format: "event: message\ndata: {json}\n\n"
        if body is None:
            return None
        for chunk in body.split("\n\n"):
            for line in chunk.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    line = line[5:].strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict) and parsed.get("id") == expected_id:
                    return parsed
        try:
            parsed = json.loads(body)
            if parsed.get("id") == expected_id:
                return parsed
        except json.JSONDecodeError:
            pass
        return None

    body, err = _post({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "teleport-measure", "version": "0.1"},
        }
    })
    if err:
        return None, f"initialize: {err}"
    init = _parse_response(body, 1)
    if not init:
        return None, f"initialize: unparseable ({body[:200] if body else 'empty'})"
    if "error" in init:
        return None, f"initialize error: {init['error']}"

    body, err = _post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    if err:
        return None, f"tools/list: {err}"
    resp = _parse_response(body, 2)
    if not resp:
        return None, f"tools/list: unparseable ({body[:200] if body else 'empty'})"
    if "error" in resp:
        return None, f"tools/list error: {resp['error']}"
    return resp.get("result", {}).get("tools", []), None


def count_tokens(tools=None):
    api_key = os.environ["ANTHROPIC_API_KEY"]
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "ping"}],
    }
    if tools is not None:
        payload["tools"] = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema") or t.get("input_schema") or {"type": "object"},
            }
            for t in tools
        ]
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages/count_tokens",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("input_tokens")


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1
    kb = json.load(open(KB))
    mcps = kb["mcps"]

    baseline = count_tokens(tools=None)
    print(f"baseline (no tools): {baseline} tokens\n")

    results = {}
    for name in TOP10:
        entry = mcps[name]
        launch = MCP_LAUNCH.get(name, {})
        print(f"[{name}] ...", flush=True)
        tools = None
        err = None
        if "pkg" in launch:
            tools, err = measure_stdio(
                launch["pkg"],
                env_vars=launch.get("env"),
                extra_args=launch.get("args"),
            )
        elif "hosted" in launch:
            tools, err = measure_hosted(launch["hosted"])
        else:
            err = "no launch config"

        if tools is None:
            print(f"  SKIP: {err}")
            results[name] = {"status": "failed", "reason": str(err)[:200]}
            continue

        with_tools = count_tokens(tools=tools)
        delta = with_tools - baseline
        print(f"  {len(tools)} tools, {with_tools} total, +{delta} over baseline")
        results[name] = {
            "tools": len(tools),
            "total_tokens": with_tools,
            "delta": delta,
        }
        entry["baseline_tokens_measured"] = delta
        entry["baseline_tokens_measured_date"] = time.strftime("%Y-%m-%d")
        entry["baseline_tokens_measured_tools"] = len(tools)

    json.dump(kb, open(KB, "w"), indent=2)

    print("\n=== Summary ===")
    ok = {k: v for k, v in results.items() if "delta" in v}
    failed = {k: v for k, v in results.items() if "delta" not in v}
    for name, r in sorted(ok.items(), key=lambda x: -x[1]["delta"]):
        print(f"  {name:<12} {r['delta']:>6} tokens  ({r['tools']} tools)")
    if failed:
        print("\nfailed:")
        for name, r in failed.items():
            print(f"  {name:<12} {r['reason']}")


if __name__ == "__main__":
    sys.exit(main() or 0)
