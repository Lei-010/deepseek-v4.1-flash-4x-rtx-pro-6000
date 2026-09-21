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

## TP=8 mem_fraction 紧急回档（2026-09-21 下午，OOM 攻坚）

事故链：0.90 OOM 循环 → 0.85 init OOM(14.10G) → 0.82 warmup prefill OOM(13.12G vs free 8.52G) → 0.78 过 warmup 但 1M prefill 尾段 OOM(968MiB vs 957.19MiB, 差11MiB) → 0.76 同点 OOM(1.29GiB vs 1.24GiB, 差50MiB, buffer随prefill推进增长) → **0.72 全通**。

根因：（sm120 MLA flash kernel）persistent grow-only buffer 按整个 KV pool 分配，TP=8 下每卡权重减半→KV pool 变大→buffer 顶爆非静态余量。TP=4@0.82 当年通过是因 pool 较小（同机制不同阈值位置）。

PATCH8：boot.py tool-call smoke 断言包 try 降级非致命（TP=8 下 DSML 工具调用偶发按纯文本吐出，断言自杀→重启循环）。

**TP=8 @ 0.72 定档结果（BENCH_RC=0）：**
- 1M context: TTFT=195.56s, prefill ~5362 tok/s（vs TP=4@0.82 基线 TTFT 214.16s，快 ~8.7%）
- max_total_num_tokens=18,028,288（vs 0.82 的 21.65M，KV pool 牺牲约 17%）
- KV 分配后余量 available_gpu_mem=24.64 GB，restarts=0，health=healthy
- 运行时显存 ~95.4/94.97...（nvidia-smi 95423 MiB used/卡）
