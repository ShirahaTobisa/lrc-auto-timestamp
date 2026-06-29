import { ChangeEvent, useMemo, useRef, useState } from "react";
import { Download, FileAudio, FileText, Play, RotateCw, Save, UploadCloud } from "lucide-react";
import { createJob, downloadLrc, getJob, getResult, saveAdjustments } from "./api";
import type { AlignedLine, JobState, TranslationMode } from "./types";

const MODEL_OPTIONS = ["base", "small", "medium", "distil-large-v3", "large-v3"];
const DEVICE_OPTIONS = ["auto", "cpu", "cuda"];
const COMPUTE_OPTIONS = ["auto", "int8", "int8_float16", "float16", "float32"];
const NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1";

export function App() {
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [lyrics, setLyrics] = useState("");
  const [modelSize, setModelSize] = useState("small");
  const [whisperDevice, setWhisperDevice] = useState("auto");
  const [whisperComputeType, setWhisperComputeType] = useState("auto");
  const [engine, setEngine] = useState("local");
  const [nvidiaApiKey, setNvidiaApiKey] = useState("");
  const [nvidiaLanguageCode, setNvidiaLanguageCode] = useState("multi");
  const [providerBaseUrl, setProviderBaseUrl] = useState(NVIDIA_BASE_URL);
  const [providerApiKey, setProviderApiKey] = useState("");
  const [providerModel, setProviderModel] = useState("openai/whisper-large-v3");
  const [translationMode, setTranslationMode] = useState<TranslationMode>("follow");
  const [job, setJob] = useState<JobState | null>(null);
  const [lines, setLines] = useState<AlignedLine[]>([]);
  const [error, setError] = useState("");
  const [isBusy, setBusy] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const audioUrl = useMemo(() => (audioFile ? URL.createObjectURL(audioFile) : ""), [audioFile]);
  const canStart = Boolean(
    audioFile &&
      lyrics.trim() &&
      !isBusy &&
      (engine === "local" || (engine === "nvidia" && nvidiaApiKey.trim()) || (engine === "compatible" && providerBaseUrl.trim() && providerApiKey.trim() && providerModel.trim()))
  );

  async function handleLyricsFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      setLyrics(await file.text());
    }
  }

  async function startJob() {
    if (!audioFile) return;
    setBusy(true);
    setError("");
    setLines([]);
    try {
      const jobId = await createJob({
        audio: audioFile,
        lyrics,
        modelSize,
        whisperDevice,
        whisperComputeType,
        engine,
        providerBaseUrl,
        providerApiKey,
        providerModel,
        nvidiaApiKey,
        nvidiaLanguageCode
      });
      await pollJob(jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function pollJob(jobId: string) {
    for (;;) {
      const next = await getJob(jobId);
      setJob(next);
      if (next.status === "done") {
        setLines(await getResult(jobId));
        return;
      }
      if (next.status === "error") {
        throw new Error(next.error || "Job failed");
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1200));
    }
  }

  function updateLine(index: number, patch: Partial<AlignedLine>) {
    setLines((current) => current.map((line) => (line.index === index ? { ...line, ...patch } : line)));
  }

  async function saveAndExport() {
    if (!job || !lines.length) return;
    setError("");
    try {
      await saveAdjustments(job.id, lines);
      const blob = await downloadLrc(job.id, translationMode);
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = href;
      link.download = `${audioFile?.name.replace(/\.[^.]+$/, "") || "lyrics"}.lrc`;
      link.click();
      URL.revokeObjectURL(href);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function playLine(ms: number | null) {
    if (!audioRef.current || ms === null) return;
    audioRef.current.currentTime = ms / 1000;
    void audioRef.current.play();
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>LRC Auto Timestamp</h1>
            <p>Local source project</p>
          </div>
          <button className="primary" disabled={!canStart} onClick={startJob}>
            {isBusy ? <RotateCw className="spin" size={18} /> : <UploadCloud size={18} />}
            Start
          </button>
        </header>

        <section className="input-grid">
          <div className="panel">
            <label className="file-drop">
              <FileAudio size={22} />
              <span>{audioFile ? audioFile.name : "Audio file"}</span>
              <input
                type="file"
                accept="audio/*,.mp3,.flac,.wav,.m4a,.ogg"
                onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <div className="settings-row">
              <label>
                Model
                <select value={modelSize} onChange={(event) => setModelSize(event.target.value)}>
                  {MODEL_OPTIONS.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Device
                <select value={whisperDevice} onChange={(event) => setWhisperDevice(event.target.value)}>
                  {DEVICE_OPTIONS.map((device) => (
                    <option key={device} value={device}>
                      {device}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Compute
                <select value={whisperComputeType} onChange={(event) => setWhisperComputeType(event.target.value)}>
                  {COMPUTE_OPTIONS.map((compute) => (
                    <option key={compute} value={compute}>
                      {compute}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Engine
                <select value={engine} onChange={(event) => setEngine(event.target.value)}>
                  <option value="local">local</option>
                  <option value="nvidia">NVIDIA Whisper (transcript)</option>
                  <option value="compatible">compatible API</option>
                </select>
              </label>
              <label>
                Translation
                <select value={translationMode} onChange={(event) => setTranslationMode(event.target.value as TranslationMode)}>
                  <option value="follow">follow vocal</option>
                  <option value="plain">plain</option>
                  <option value="timestamped">own time</option>
                </select>
              </label>
            </div>
            {engine === "nvidia" && (
              <div className="provider-grid">
                <label>
                  Server
                  <input value="grpc.nvcf.nvidia.com:443" readOnly />
                </label>
                <label>
                  Language
                  <input value={nvidiaLanguageCode} onChange={(event) => setNvidiaLanguageCode(event.target.value)} placeholder="multi" />
                </label>
                <label>
                  API key
                  <input type="password" value={nvidiaApiKey} onChange={(event) => setNvidiaApiKey(event.target.value)} autoComplete="off" />
                </label>
              </div>
            )}
            {engine === "compatible" && (
              <div className="provider-grid">
                <label>
                  Base URL
                  <input value={providerBaseUrl} onChange={(event) => setProviderBaseUrl(event.target.value)} placeholder={NVIDIA_BASE_URL} />
                </label>
                <label>
                  Model
                  <input value={providerModel} onChange={(event) => setProviderModel(event.target.value)} placeholder="openai/whisper-large-v3" />
                </label>
                <label>
                  API key
                  <input type="password" value={providerApiKey} onChange={(event) => setProviderApiKey(event.target.value)} autoComplete="off" />
                </label>
              </div>
            )}
            {audioUrl && <audio ref={audioRef} src={audioUrl} controls className="audio-player" />}
          </div>

          <div className="panel lyrics-panel">
            <div className="panel-title">
              <FileText size={18} />
              <span>Lyrics</span>
              <label className="icon-button" title="Load lyric file">
                <UploadCloud size={16} />
                <input type="file" accept=".lrc,.txt" onChange={handleLyricsFile} />
              </label>
            </div>
            <textarea value={lyrics} onChange={(event) => setLyrics(event.target.value)} spellCheck={false} />
          </div>
        </section>

        {job && (
          <section className="status-strip">
            <span>{job.message}</span>
            <progress value={job.progress} max={1} />
            <span>{Math.round(job.progress * 100)}%</span>
          </section>
        )}
        {error && <section className="error-strip">{error}</section>}

        <section className="result-panel">
          <div className="result-header">
            <h2>Aligned Lines</h2>
            <button className="secondary" disabled={!lines.length || !job} onClick={saveAndExport}>
              <Save size={17} />
              <Download size={17} />
              Export
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Type</th>
                  <th>Lyric</th>
                  <th>Score</th>
                  <th>Play</th>
                </tr>
              </thead>
              <tbody>
                {lines.length ? (
                  lines.map((line) => (
                    <tr key={line.index} className={line.warnings.length ? "warn" : ""}>
                      <td>
                        <input
                          className="time-input"
                          value={formatTimeInput(line.start_ms)}
                          onChange={(event) => updateLine(line.index, { start_ms: parseTimeInput(event.target.value) })}
                        />
                      </td>
                      <td>
                        <select
                          value={line.line_type}
                          onChange={(event) => updateLine(line.index, { line_type: event.target.value as AlignedLine["line_type"] })}
                        >
                          <option value="vocal">vocal</option>
                          <option value="translation">translation</option>
                        </select>
                      </td>
                      <td>
                        <input className="lyric-input" value={line.text} onChange={(event) => updateLine(line.index, { text: event.target.value })} />
                      </td>
                      <td>{Math.round(line.confidence * 100)}%</td>
                      <td>
                        <button className="icon-button" title="Play line" onClick={() => playLine(line.start_ms)}>
                          <Play size={16} />
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="empty-state">
                      No aligned lines
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}

function formatTimeInput(ms: number | null): string {
  if (ms === null) return "";
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  const centiseconds = Math.floor((ms % 1000) / 10);
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(centiseconds).padStart(2, "0")}`;
}

function parseTimeInput(value: string): number | null {
  const match = value.trim().match(/^(\d+):(\d{2})(?:[.:](\d{1,3}))?$/);
  if (!match) return null;
  const fraction = match[3] ?? "0";
  const millis = fraction.length === 1 ? Number(fraction) * 100 : fraction.length === 2 ? Number(fraction) * 10 : Number(fraction.slice(0, 3));
  return Number(match[1]) * 60000 + Number(match[2]) * 1000 + millis;
}
