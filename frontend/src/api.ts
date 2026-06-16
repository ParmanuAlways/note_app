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

export interface EventRecord {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  venue: string | null;
  attendees: string | null;
  rrule: string | null;
  classification: string | null;
}

export interface EventInput {
  title: string;
  starts_at: string;
  ends_at?: string | null;
  venue?: string | null;
  attendees?: string | null;
}

export async function listEvents(): Promise<EventRecord[]> {
  const res = await fetch(`${BASE}/events`);
  if (!res.ok) throw new Error(`events ${res.status}`);
  return res.json();
}

export async function createEvent(input: EventInput): Promise<EventRecord> {
  const res = await fetch(`${BASE}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`create failed ${res.status}`);
  return res.json();
}
