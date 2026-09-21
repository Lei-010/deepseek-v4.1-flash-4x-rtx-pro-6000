"""Reproduce DSML tool-call degradation on live server (TP=8, DSPARK on)."""
import json, urllib.request, time

KEY = open("/ssd/dsv41/state/api-key").read().strip()

def req(body, timeout=300):
    r = urllib.request.Request("http://127.0.0.1:8000/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))

tools = [{"type": "function", "function": {
    "name": "get_weather",
    "description": "Get current weather for a city",
    "parameters": {"type": "object", "properties": {
        "city": {"type": "string"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}},
        "required": ["city"]}}}]

cities = ["Beijing", "Tokyo", "Paris", "London", "Berlin", "Sydney",
          "Toronto", "Moscow", "Dubai", "Singapore", "Seoul", "Rome"]

results = []
for i, c in enumerate(cities):
    body = {"model": "deepseek-v4.1-flash",
            "messages": [{"role": "user",
                          "content": f"What is the weather in {c} right now? Use the get_weather tool."}],
            "tools": tools, "tool_choice": "auto",
            "temperature": 0, "max_tokens": 512}
    t0 = time.time()
    try:
        out = req(body)
        msg = out["choices"][0]["message"]
        tc = msg.get("tool_calls") or []
        entry = {"i": i, "city": c, "ok": len(tc) > 0, "dt": round(time.time() - t0, 1)}
        if tc:
            entry["fn"] = tc[0]["function"]["name"]
            entry["args"] = tc[0]["function"]["arguments"][:120]
        else:
            entry["content_head"] = (msg.get("content") or "")[:400]
            entry["reasoning_head"] = (msg.get("reasoning_content") or "")[:200]
        if msg.get("reasoning_content"):
            entry["had_reasoning"] = True
    except Exception as e:
        entry = {"i": i, "city": c, "ok": False, "err": repr(e)[:200],
                 "dt": round(time.time() - t0, 1)}
    results.append(entry)
    print(json.dumps(entry, ensure_ascii=False), flush=True)

ok = sum(1 for r in results if r["ok"])
summary = {"total": len(results), "structured": ok, "degraded": len(results) - ok}
print("SUMMARY", json.dumps(summary), flush=True)
with open("/ssd/dsv41/state/dsml_repro.json", "w") as f:
    f.write(json.dumps({"summary": summary, "results": results}, indent=2))
