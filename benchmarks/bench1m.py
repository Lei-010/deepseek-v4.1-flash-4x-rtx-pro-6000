#!/usr/bin/env python3
"""1M prefill single functional test (0.85 config): does full-length context actually run?"""
import json, time
import urllib.request

BASE = "http://127.0.0.1:8000"
KEY = open("/state/api-key").read().strip()

def req(path, data=None, timeout=3600):
    r = urllib.request.Request(BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    return urllib.request.urlopen(r, timeout=timeout)

# wait ready
t0 = time.time()
while time.time() - t0 < 900:
    try:
        req("/v1/models", None, timeout=10)
        break
    except Exception:
        time.sleep(10)
else:
    print("SERVER_NOT_READY"); raise SystemExit(1)
print("server ready", flush=True)

unit = ("The mitochondrion is a double-membrane-bound organelle found in most eukaryotic organisms. "
        "Mitochondria generate most of the cell's supply of adenosine triphosphate. ")
prompt = unit * (4 * 1024 * 1024 // len(unit) + 1)  # ~4MiB chars ~ 1M tokens
est = len(prompt) // 4
print(f"prompt chars={len(prompt)} est_tokens={est}", flush=True)

payload = {"model": "deepseek-v41",
           "messages": [{"role": "user", "content": prompt + "\n\nSummarize the passage in one sentence."}],
           "max_tokens": 64, "stream": True, "ignore_eos": True}
ts = time.time()
resp = req("/v1/chat/completions", payload, 3600)
ttft = None; ntok = 0; t_last = ts
for line in resp:
    line = line.decode().strip()
    if not line.startswith("data: "): continue
    data = line[6:]
    if data == "[DONE]": break
    try: j = json.loads(data)
    except: continue
    d = j.get("choices", [{}])[0].get("delta", {})
    if d.get("content"):
        ntok += 1
        now = time.time()
        if ttft is None: ttft = now - ts
        t_last = now
if ttft is None:
    print("NO_TOKENS server likely crashed"); raise SystemExit(2)
r = {"ctx": "1M", "est_tokens": est, "ttft_s": round(ttft, 2),
     "prefill_tok_s_est": round(est / ttft, 0), "out_tokens": ntok}
json.dump(r, open("/state/bench-1m.json", "w"), indent=2)
print("1M " + json.dumps(r), flush=True)
print("== BENCH1M_DONE ==", flush=True)
