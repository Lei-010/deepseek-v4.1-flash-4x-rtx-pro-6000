#!/usr/bin/env python3
"""DSV4.1-Flash benchmark v3 (0.85/1M): T1 single, T2 8-conc, T3 prefill 128K/256K/512K."""
import json, time, threading
import urllib.request

BASE = "http://127.0.0.1:8000"
KEY = open("/state/api-key").read().strip()

def req(path, data=None, timeout=1800):
    r = urllib.request.Request(BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    return urllib.request.urlopen(r, timeout=timeout)

def chat(prompt, max_tokens, stream=False, timeout=1800):
    payload = {"model": "deepseek-v41", "messages": [{"role": "user", "content": prompt}],
               "max_tokens": max_tokens, "stream": stream, "ignore_eos": True}
    t0 = time.time()
    resp = req("/v1/chat/completions", payload, timeout)
    if not stream:
        body = json.loads(resp.read())
        return t0, time.time(), body["usage"]
    ttft = None; ntok = 0; t_last = t0
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
            if ttft is None: ttft = now - t0
            t_last = now
    if ttft is None:
        raise RuntimeError("no tokens received")
    return t0, t_last, {"ttft": ttft, "completion_tokens": ntok}

def wait_ready(max_wait=900):
    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            req("/v1/models", None, timeout=10)  # GET, no body
            return True
        except Exception:
            time.sleep(10)
    return False

results = {}
if not wait_ready():
    print("SERVER_NOT_READY"); raise SystemExit(1)
print("server ready", flush=True)

# T1 single-stream decode
t0, t1, u = chat("Write a detailed technical essay about protein folding.", 512, stream=True)
dec = u["completion_tokens"]
r1 = {"ttft_s": round(u["ttft"], 3), "decode_tokens": dec,
      "decode_tok_s": round(dec / (t1 - t0 - u["ttft"]), 1)}
print("T1 " + json.dumps(r1), flush=True)
results["single_stream"] = r1

# T2 8 concurrent
CONC, OT = 8, 256
agg = {"tok": 0, "lock": threading.Lock()}
def worker(i):
    t0w, t1w, uw = chat(f"Explain topic {i}: nuclear receptor signaling pathways in detail.", OT)
    with agg["lock"]:
        agg["tok"] += uw.get("completion_tokens", OT)
threads = [threading.Thread(target=worker, args=(i,)) for i in range(CONC)]
ts = time.time()
for th in threads: th.start()
for th in threads: th.join()
el = time.time() - ts
r2 = {"concurrency": CONC, "out_per_req": OT, "wall_s": round(el, 2),
      "total_tokens": agg["tok"], "aggregate_tok_s": round(agg["tok"] / el, 1)}
print("T2 " + json.dumps(r2), flush=True)
results["concurrent_8"] = r2

# T3 prefill 128K / 256K / 512K
unit = ("The mitochondrion is a double-membrane-bound organelle found in most eukaryotic organisms. "
        "Mitochondria generate most of the cell's supply of adenosine triphosphate. ")
for target_chars, label in [(512*1024, "128K"), (1024*1024, "256K"), (2*1024*1024, "512K")]:
    prompt = unit * (target_chars // len(unit) + 1)
    try:
        t0, t1, u = chat(prompt + "\n\nSummarize the passage in one sentence.", 64, stream=True)
        est_tokens = len(prompt) // 4
        r = {"ctx_label": label, "ttft_s": round(u["ttft"], 2),
             "prefill_tok_s_est": round(est_tokens / u["ttft"], 0)}
    except Exception as e:
        r = {"ctx_label": label, "error": str(e)[:120]}
    print("T3 " + json.dumps(r), flush=True)
    results[f"prefill_{label}"] = r
    if "error" in r: break

json.dump(results, open("/state/bench-results.json", "w"), indent=2)
print("== BENCH3_DONE ==", flush=True)
print(json.dumps(results, indent=2), flush=True)
