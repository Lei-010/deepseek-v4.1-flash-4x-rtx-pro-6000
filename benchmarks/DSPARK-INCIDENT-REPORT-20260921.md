# DeepSeek-V4.1-Flash @ gpu01 — DSPARK 正确性事故报告与三档 Benchmark

日期：2026-09-21 · 硬件：8× RTX PRO 6000 Max-Q (SM120, 单卡 94.97 GiB) · TP=8 / mem_fraction=0.72 · commit `faa3403`（本报告后追加 commit）

## TL;DR

**DSPARK 投机解码在当前镜像（sglang 0.0.0.dev0, pin `sha256:c4ca65…`）上存在静默 token 损坏缺陷，DSML tool-call 解析退化与 vision 400 错误同源于此。生产配置定案为 `SPEC_ALGORITHM=none`。** 该缺陷在上游 sglang #34959 有完整记录，修复 PR #34189 不在我们的 pinned 镜像内；`block_size=3`（上游报告的零损坏窗口）在本地实测仍 12/12 退化，不可用。

## 根因链（A/B 实测）

| 配置 | DSML tool-call（12 次复现） | Vision | 1M prefill TTFT | 单流 decode |
|------|---------------------------|--------|-----------------|-------------|
| DSPARK on, block=6 | **12/12 全退化**（属性重复/双空格标签变形） | 400 math domain error | 195.56 s | 43.6 tok/s |
| DSPARK on, block=3 | **12/12 全退化**（直接吐裸 JSON，不发标签） | 未测 | 未测 | 未测 |
| **DSPARK off（生产定案）** | **12/12 全成功** | **正常**（1024 image tokens，正确描述） | **126.77 s** | 34.0 tok/s |

DSPARK on 的失败输出特征：`<｜DSML｜  invoke` 双空格、`name="..." name="..."` 属性重复——draft/verify 对齐失败特征。#34959 报告者实测 verify 窗口 > c4 KV 压缩比（=4）时损坏率跳变（block=6 → 0.51%；block=3 → 0/7499），但该零损坏结论依赖含 PR #34189 修复的新版本；我们旧版镜像仅缩窗口无效（block=3 仍全退化）。

## 上游记录

- **#34959**（2026-08-15 提交，08-22 关闭）：「DSPARK silently corrupts identifiers on DeepSeek-V4-Flash, making speculative decoding unsafe」[来源: https://github.com/sgl-project/sglang/issues/34959]
- **#33985**（2026-08-07，仍 Open）：SM120 上 DSPARK draft attention topk=192 无 decode kernel 实例化——Dockerfile 中 COPY 的自定义 `flash_mla_sm120.py` 即绕过该问题的 shim [来源: https://github.com/sgl-project/sglang/issues/33985]

## 工程修复（已烧入镜像）

1. **boot.py PATCH9**：`SPEC_ALGORITHM=dspark|none` + `DSPARK_BLOCK_SIZE` 环境变量开关；根因注释固化（防止后人重启镜像后 DSPARK 复活踩同坑）
2. **run_dsv41.sh**：env 透传（`-e SPEC_ALGORITHM=${SPEC_ALGORITHM:-dspark}` 等，默认值保持 dspark 以便未来镜像升级后回归验证）
3. 修复脚本：`patch_env_spec.py` / `patch_run_passthrough.py` / `fix_run_comment.py` / `patch9_boot.py`（本地留档 `/Users/lei/.hermes/cache/scratch/`）

## 三档 Benchmark（bench3b + bench1m）

### DSPARK OFF（生产定案档）

| 指标 | 数值 |
|------|------|
| 单流 decode | 34.0 tok/s（TTFT 0.116s） |
| 并发×8 聚合 | 285.9 tok/s |
| Prefill 128K | 9,629 tok/s |
| Prefill 256K | 16,452 tok/s |
| Prefill 512K | 12,972 tok/s |
| **1M TTFT** | **126.77 s**（8,272 tok/s） |

### DSPARK ON block=6（事故档，仅历史参考）

| 指标 | 数值 |
|------|------|
| 单流 decode | 43.6 tok/s |
| 1M TTFT | 195.56 s |

### DSPARK ON block=3（已证不可用）

DSML 12/12 退化 → 正确性档不成立，不进入生产候选。

## 结论与后续

1. **生产 = `SPEC_ALGORITHM=none`**：DSML/vision 全功能正确 + 1M prefill 快 54%（126.77 vs 195.56s）。decode 损失 22%（34.0 vs 43.6 tok/s），以长上下文为主负载的当前用例下 off 档全面占优。
2. DSPARK 重新启用条件：镜像升级到含 PR #34189 的 sglang 版本后，重跑本报告 A/B（dsml_repro.py 12 次 + vision_repro.py）验证。
3. vision 修复项关闭（PATCH7c Rust 假设推翻，无独立修复）。
4. PATCH8 降级规避保留为 tripwire。
