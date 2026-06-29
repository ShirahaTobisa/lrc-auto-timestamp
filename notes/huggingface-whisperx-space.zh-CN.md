# Hugging Face Spaces 部署 WhisperX 打轴服务

结论：可以部署。推荐先做 Gradio Space，GPU 选 `t4-small` 起步；CPU Basic 免费但只适合短音频测试。

## 为什么用 Spaces

- Hugging Face Spaces 是 git 仓库式部署，提交后会自动 rebuild/restart。
- 新建 Space 时可选 Gradio、Docker、Static HTML。
- 默认免费 CPU 是 2 vCPU、16 GB RAM、50 GB 临时磁盘；WhisperX 打轴建议升 GPU。
- 密钥不要写进代码，Space Settings 里用 Secrets。

来源：HF Spaces overview、GPU、dependencies、configuration docs。

## 最短部署步骤

1. 打开 https://huggingface.co/new-space
2. 选择 `Gradio`，Visibility 建议先 `Private`。
3. 创建后 clone 这个 Space 仓库。
4. 把本项目 `hf-space/` 目录里的文件复制到 Space 仓库根目录：
   - `README.md`
   - `app.py`
   - `requirements.txt`
   - `packages.txt`
5. push 到 Hugging Face。
6. Space Settings 里把 Hardware 升到 `t4-small` 或更高。
7. 打开 Space，上传音频和无轴歌词测试。

## 关键文件说明

`README.md` 顶部 YAML 用于配置 Space：

```yaml
sdk: gradio
python_version: 3.10
suggested_hardware: t4-small
```

`requirements.txt` 安装 PyTorch、Gradio、WhisperX。

`packages.txt` 安装 Debian 依赖，主要是 `ffmpeg`、`rustc`、`cargo`。

## WhisperX 处理链

WhisperX 官方 Python 示例是：

```python
model = whisperx.load_model("large-v2", device, compute_type=compute_type)
audio = whisperx.load_audio(audio_file)
result = model.transcribe(audio, batch_size=batch_size)
model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device)
```

本项目的 `hf-space/app.py` 就是这个流程的最小 Gradio 包装。

## 成本和效果

- CPU Basic：免费，但很慢，适合验证构建。
- T4 small：16 GB 显存，适合 `large-v3` 小批量测试。
- L4/A10G：更稳，适合更长音频或多人使用。
- WhisperX 能给 word-level timestamp，但不同语言依赖对应 alignment model；中文/日文/韩文歌词可能需要实际测试。

## 对接本地项目

第一阶段可以直接用 Space 网页输出 LRC。

第二阶段再给 Space 加 FastAPI endpoint，让本地项目把音频和歌词 POST 到 Space，返回：

```json
{
  "lrc": "...",
  "segments": [],
  "words": []
}
```

这样本地工具里可以新增一个 `Hugging Face Space` 引擎，填 Space URL 即可。

## 参考资料

- Hugging Face Spaces Overview: https://huggingface.co/docs/hub/spaces-overview
- Gradio Spaces dependencies: https://huggingface.co/docs/hub/spaces-dependencies
- GPU Spaces: https://huggingface.co/docs/hub/spaces-gpus
- Spaces configuration reference: https://huggingface.co/docs/hub/spaces-config-reference
- Docker Spaces: https://huggingface.co/docs/hub/spaces-sdks-docker
- WhisperX README: https://github.com/m-bain/whisperX

