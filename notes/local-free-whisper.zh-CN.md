# 免费本地 Whisper 部署路线

结论：免费、稳定、可长期用的路线是本地 `faster-whisper`。你这台机器有 RTX 4060 Laptop 8GB 和 ffmpeg，适合本地跑；当前只看到 Python 3.14，需要另外装 Python 3.11 或 3.12。

## 推荐模型

- `small`：先跑通，速度快，准确度一般。
- `medium`：8GB 显存可尝试，速度和准确率折中。
- `large-v3` / `distil-large-v3`：更准，但显存和 CUDA 库要求更高。

项目 UI 里第一版先给 `base/small/medium`，建议默认 `small`，跑通后再改 `medium`。

## 安装步骤

1. 安装 Python 3.11 或 3.12。
2. 进入项目：

```powershell
cd D:\tools\codex\project\lrc-auto-timestamp
```

3. 安装本地 Whisper 依赖：

```powershell
.\scripts\setup-local-whisper.ps1
```

4. 启动后端：

```powershell
.\scripts\start-backend.ps1
```

5. 前端：

```powershell
cd frontend
npm install
npm run dev
```

6. 页面里选择：

```text
Engine: local
Model: small
```

## GPU 注意事项

`faster-whisper` 基于 CTranslate2。官方 README 写明 GPU 需要 CUDA 12 的 cuBLAS 和 cuDNN 9；Windows 上如果缺这些库，可能会报 DLL/cuDNN 相关错误。

处理方式：

- 先用 CPU/int8 跑通。
- 再装 CUDA/cuDNN 或使用 faster-whisper README 里提到的 Windows 运行库方案。
- 如果 GPU 路线折腾，仍然可以用 CPU `base/small`，只是慢。

## 为什么不用 HF 免费 CPU

Hugging Face Spaces 免费 CPU 可以部署，但 WhisperX/Whisper 打轴对算力要求高。短音频可以试，完整歌曲会慢，排队和休眠也会影响体验。真正“免费且稳定”的还是本机跑。

## 参考

- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- WhisperX: https://github.com/m-bain/whisperX

