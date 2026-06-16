// All requests are same-origin / proxied to the local backend. No external host.

export interface SystemStatus {
  inference: {
    extraction: string;
    transcription: string;
    embedding: string;
  };
  disk: { total_gb: number; used_gb: number; free_gb: number };
  queue_depth: number | null;
  gpu: unknown | null;
  last_backup_at: string | null;
}

const BASE = "/api";

export async function getStatus(): Promise<SystemStatus> {
  const res = await fetch(`${BASE}/status`);
  if (!res.ok) throw new Error(`status ${res.status}`);
  return res.json();
}
