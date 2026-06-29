import type { AlignedLine, JobState, TranslationMode } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function createJob(params: {
  audio: File;
  lyrics: string;
  modelSize: string;
  whisperDevice: string;
  whisperComputeType: string;
  engine: string;
  providerBaseUrl: string;
  providerApiKey: string;
  providerModel: string;
  nvidiaApiKey: string;
  nvidiaLanguageCode: string;
}): Promise<string> {
  const form = new FormData();
  form.append("audio", params.audio);
  form.append("lyrics", params.lyrics);
  form.append("model_size", params.modelSize);
  form.append("whisper_device", params.whisperDevice);
  form.append("whisper_compute_type", params.whisperComputeType);
  form.append("engine", params.engine);
  form.append("provider_base_url", params.providerBaseUrl);
  form.append("provider_api_key", params.providerApiKey);
  form.append("provider_model", params.providerModel);
  form.append("nvidia_api_key", params.nvidiaApiKey);
  form.append("nvidia_language_code", params.nvidiaLanguageCode);

  const response = await fetch(`${API_BASE}/api/jobs`, {
    method: "POST",
    body: form
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const data = (await response.json()) as { job_id: string };
  return data.job_id;
}

export async function getJob(jobId: string): Promise<JobState> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as JobState;
}

export async function getResult(jobId: string): Promise<AlignedLine[]> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}/result`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const data = (await response.json()) as { lines: AlignedLine[] };
  return data.lines;
}

export async function saveAdjustments(jobId: string, lines: AlignedLine[]): Promise<void> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}/adjust`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lines })
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
}

export async function downloadLrc(jobId: string, translationMode: TranslationMode): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/jobs/${jobId}/export.lrc?translation_mode=${translationMode}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return await response.blob();
}
