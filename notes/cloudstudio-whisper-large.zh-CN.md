# CloudStudio 部署 Whisper large-v3

CloudStudio 有 GPU 规格时可以部署。按你截图里的资源表，优先选 `GPU T4`；如果想更快再选 `GPU A10`。A100/A800/L40 对歌词打轴过剩。

## 推荐配置

- 规格：`GPU T4`
- 模型：`large-v3`
- Device：`cuda`
- Compute：`int8_float16`

如果 T4 速度或显存不舒服，降到 `distil-large-v3` 或 `medium`。

## 导入仓库后安装

```bash
cd lrc-auto-timestamp
bash scripts/setup-cloudstudio.sh
```

启动后端：

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

CloudStudio 里把 `8000` 端口开放或预览。

前端如果也在 CloudStudio 跑：

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

再开放 `5173` 端口。

## 页面选项

```text
Engine: local
Model: large-v3
Device: cuda
Compute: int8_float16
```

如果报 CUDA/cuDNN/CUBLAS 相关错误，先改：

```text
Model: medium
Device: cpu
Compute: int8
```

确认流程通了，再修 GPU 依赖。

## 验证 GPU

```bash
nvidia-smi
python - <<'PY'
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cuda", compute_type="int8_float16")
print("ok")
PY
```

