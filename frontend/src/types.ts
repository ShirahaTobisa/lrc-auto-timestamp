export type JobStatus = "queued" | "processing" | "done" | "error";
export type LineType = "vocal" | "translation";

export interface JobState {
  id: string;
  status: JobStatus;
  progress: number;
  message: string;
  error?: string | null;
}

export interface AlignedLine {
  index: number;
  text: string;
  line_type: LineType;
  start_ms: number | null;
  confidence: number;
  warnings: string[];
}

export type TranslationMode = "follow" | "plain" | "timestamped";

