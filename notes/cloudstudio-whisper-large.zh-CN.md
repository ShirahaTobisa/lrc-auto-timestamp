# CloudStudio 部署 Whisper large-v3

CloudStudio 有 GPU 规格时可以部署。计算单元由你在 CloudStudio 顶部 UI 里选择，仓库只负责提供运行配置。

## 模型建议

- 模型：`large-v3`
- Device：`cuda`
- Compute：`int8_float16`

如果当前计算单元速度或显存不舒服，降到 `distil-large-v3` 或 `medium`。

## 直接运行

仓库包含 `.vscode/preview.yml`，CloudStudio 点击顶部“运行”会执行：

```bash
bash scripts/cloudstudio-run.sh
```

这个脚本会：

- 确认 `ffmpeg`。
- 创建 `.venv`。
- 安装后端本地 Whisper 依赖。
- 安装前端依赖。
- 在内部启动后端 `127.0.0.1:8000`。
- 对外预览前端 `0.0.0.0:5173`。

前端通过 Vite proxy 访问后端，所以只需要预览 `5173`。

## 页面选项

```text
Engine: local
Model: large-v3
Device: cuda
Compute: int8_float16
```

打轴质量优先依赖词级时间戳。本项目本地模式会启用 faster-whisper 的 `word_timestamps=True`，再用词时间窗口匹配已有歌词行。

计算单元不用写进仓库配置，直接在 CloudStudio 顶部下拉选择。

如果报 CUDA/cuDNN/CUBLAS 相关错误，先改：

```text
Model: medium
Device: cpu
Compute: int8
```

确认流程通了，再修 GPU 依赖。

如果看到 `[json.exception.parse_error.101]`，通常是模型缓存下载坏了。删除对应 Hugging Face/CTranslate2 模型缓存后重新运行。

## 验证 GPU

```bash
nvidia-smi
python - <<'PY'
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cuda", compute_type="int8_float16")
print("ok")
PY
```
