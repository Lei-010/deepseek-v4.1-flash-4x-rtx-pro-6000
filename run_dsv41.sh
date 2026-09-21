#!/bin/bash
set -e
cd /ssd/dsv41
docker build -t deepseek-v41-4x6000:local . > /tmp/build.log 2>&1 || true
docker rm -f dsv41 2>/dev/null || true
docker run -d --name dsv41 \
  --runtime nvidia -e NVIDIA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
  --network host --ipc host \
  --cap-add IPC_LOCK --ulimit memlock=-1 \
  --restart unless-stopped \
  -v /ssd/DeepSeek-V4.1-Flash:/models/DeepSeek-V4.1-Flash \
  -v /ssd/dsv41/state:/state \
  -e OFFLOAD_MODE=nvme \
  -e DSV41_CACHE_GIB=64 \
  -e CONTEXT_LENGTH=1048576 \
  -e CHUNKED_PREFILL_SIZE=2048 \
  -e MEMORY_FRACTION=0.72 \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -e MAX_RUNNING_REQUESTS=8 \
  -e SERVER_PORT=8000 \
  -e HF_META_BASE=https://hf-mirror.com \
  -e HTTPS_PROXY=http://127.0.0.1:18888 \
  -e HTTP_PROXY=http://127.0.0.1:18888 \
  -e https_proxy=http://127.0.0.1:18888 \
  -e http_proxy=http://127.0.0.1:18888 \
  -e NO_PROXY=localhost,127.0.0.1 \
  -e no_proxy=localhost,127.0.0.1 \
  deepseek-v41-4x6000:local
sleep 8
docker ps -a --filter name=dsv41 --format status:{{.Status}}
docker logs dsv41 2>&1 | tail -15
echo LAUNCHER_DONE
