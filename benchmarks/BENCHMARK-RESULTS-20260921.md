# DeepSeek-V4.1-Flash — gpu01 Benchmark Results (2026-09-21)

## Configuration
- Hardware: gpu01, TP=4 (4x RTX PRO 6000 Max-Q, 94.97 GiB/GPU), PCIe-only (no NVLink)
- Runtime: SGLang, mem_fraction_static=0.82, KV cache fp8_e4m3 (no scaling factors, default 1.0)
- moe_runner_backend=flashinfer_mxfp4; triton_attn multimodal; container dsv41 39efb10c15b7
- mem_fraction_static search: 0.85 -> 1M prefill OOM (1.42 GiB short); 0.80 -> startup crash (SWA pool 0.58 GB cannot fit); 0.82 -> all pass

## Results (bench3b + bench1m, 2026-09-21)
- single_stream: TTFT 0.142s, decode 25.1 tok/s (216 tokens)
- concurrent x8: aggregate 150.7 tok/s (256 tok/req, wall 13.59s, 2048 total)
- prefill 128K: TTFT 15.57s, est 8,422 tok/s
- prefill 256K: TTFT 17.87s, est 14,667 tok/s
- prefill 512K: TTFT 44.96s, est 11,663 tok/s
- prefill 1M:   TTFT 214.16s, est 4,896 tok/s (est_tokens=1,048,580)  <- new capability at 0.82

## Baseline comparison (0.85 vs 0.82)
- 128K: 8,335 -> 8,422 tok/s; 256K: 14,171 -> 14,667; 512K: 11,598 -> 11,663 (no regression)
- 1M: OOM -> PASS

## Reproduce
docker cp benchmarks/bench3b.py dsv41:/tmp/ && docker exec dsv41 python3 /tmp/bench3b.py
docker cp benchmarks/bench1m.py dsv41:/tmp/ && docker exec dsv41 python3 /tmp/bench1m.py
(scripts read key from /state/api-key, target 127.0.0.1:8000 inside container)
