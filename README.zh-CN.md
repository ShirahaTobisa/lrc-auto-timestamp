# LRC Auto Timestamp

一个本地运行的源码项目，用来把“音乐文件 + 无时间轴歌词”自动生成逐行 LRC 时间轴。项目不提供在线服务：用户 clone 到自己的电脑后运行，FastAPI 后端负责转写和对齐，Vite + React 前端负责上传、预览、手动微调和导出。

## 状态

- 本地网页工具骨架已实现。
- 后端支持歌词解析、ffmpeg 转换、本地 `faster-whisper` 转写、可选 OpenAI-compatible 转写服务、歌词对齐、结果调整和 LRC 导出。
- 前端支持上传音频、粘贴/读取歌词、查看任务进度、逐行编辑、单行试听、翻译行处理和导出。
- 歌词模式支持 `align` 和 `generate`：有歌词时对齐已有歌词；没有歌词时用 Whisper 转写结果生成 LRC 草稿。

## 环境要求

- 推荐 Python 3.11 或 3.12。
- 推荐 Node.js 22。
- `ffmpeg` 已安装并在 `PATH` 中可用。
- 第一次使用 `faster-whisper` 时会在用户本机模型缓存目录下载模型；仓库不会提交模型文件。

## 安装

只用免费本地 Whisper 时：

```powershell
cd project\lrc-auto-timestamp
.\scripts\setup-local-whisper.ps1
```

完整依赖安装：

```powershell
cd project\lrc-auto-timestamp
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd frontend
npm install
```

## 运行

打开两个终端：

```powershell
cd project\lrc-auto-timestamp
.\scripts\start-backend.ps1
```

```powershell
cd project\lrc-auto-timestamp
.\scripts\start-frontend.ps1
```

然后访问 `http://127.0.0.1:5173`。

Windows 下也可以运行 `.\scripts\start-dev.ps1`，它会分别打开后端和前端窗口。

CloudStudio 导入仓库后可以直接点顶部“运行”。仓库里的 `.vscode/preview.yml` 会调用 `scripts/cloudstudio-run.sh`，自动启动后端和前端；计算单元在 CloudStudio UI 里选择。

## 本地隐私边界

- 默认 `local` 引擎不会上传音频或歌词。
- 用户音频、临时 WAV、任务结果都保存在 `backend/storage/`，该目录已被 git 忽略。
- Whisper/faster-whisper 模型下载到用户本机缓存目录，不进入仓库。
- `NVIDIA Whisper` 引擎使用 NVIDIA build 页面对应的 Riva gRPC endpoint：`grpc.nvcf.nvidia.com:443`，并携带 Whisper function ID。
- `compatible API` 引擎保留给真正提供 `/v1/audio/transcriptions` 的 provider。
- API key 在本地网页界面按本次请求输入，本项目不会把它写入环境变量或文件。
- 选择兼容云端引擎后，音频会发送到对应 provider。

不保存凭据的 provider 探测：

```powershell
cd project\lrc-auto-timestamp
.\scripts\probe-provider.ps1
```

探测脚本会隐藏输入 API key，并测试 NVIDIA 的 Riva gRPC endpoint。

## 对齐行为

- 对齐前会移除旧 LRC 时间标签和常见元数据标签。
- 空行会被忽略。
- 明显的翻译行会保留，但不作为自动对齐锚点。
- 演唱行按顺序匹配转写片段；低置信度或估算行会被标记，方便人工检查。
- `generate` 模式不需要输入歌词，会直接把转写片段变成可编辑 LRC 行。
- 如果云端 provider 只返回整段 transcript、没有词级或片段级时间，相关行会被标成 `estimated/low_confidence`。
- 导出模式：
  - `follow vocal`：翻译行沿用上一条演唱行时间。
  - `plain`：翻译行不加时间戳。
  - `own time`：翻译行使用自身保存的时间。

## 测试

核心解析和对齐测试不需要 Whisper 模型：

```powershell
cd project\lrc-auto-timestamp\backend
python -m pytest
```

## 重要文件

- `backend/app/lrc.py`：歌词解析和 LRC 导出。
- `backend/app/alignment.py`：按顺序匹配歌词行和转写片段。
- `backend/app/transcription.py`：ffmpeg、faster-whisper 和可选 OpenAI-compatible 转写。
- `backend/app/main.py`：FastAPI 接口。
- `frontend/src/App.tsx`：本地网页工具界面。
- `scripts/`：Windows 启动脚本。
- `hf-space/`：可复制到 Hugging Face Spaces 的 WhisperX 打轴服务模板。
- `notes/local-free-whisper.zh-CN.md`：免费本地 Whisper 部署说明。
- `notes/cloudstudio-whisper-large.zh-CN.md`：CloudStudio GPU 部署 large-v3 说明。
- `notes/huggingface-whisperx-space.zh-CN.md`：Hugging Face Spaces 部署教程。

## 备注

第一版目标是逐行时间轴，不做逐字卡拉 OK 时间轴。
