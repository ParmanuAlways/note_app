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

// One concrete instance returned by the backend after expanding recurrence.
export interface Occurrence {
  event_id: string;
  title: string;
  occurrence_start: string;
  occurrence_end: string | null;
  venue: string | null;
  attendees: string | null;
  classification: string | null;
  rrule: string | null;
  is_recurring: boolean;
  is_override: boolean;
}

export interface EventInput {
  title: string;
  starts_at: string;
  ends_at?: string | null;
  venue?: string | null;
  attendees?: string | null;
  rrule?: string | null;
}

export async function listEvents(start: string, end: string): Promise<Occurrence[]> {
  const res = await fetch(`${BASE}/events?start=${start}&end=${end}`);
  if (!res.ok) throw new Error(`events ${res.status}`);
  return res.json();
}

export async function createEvent(input: EventInput): Promise<unknown> {
  const res = await fetch(`${BASE}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`create failed ${res.status}`);
  return res.json();
}

// scope=series deletes the whole series; scope=occurrence needs the instance start.
export async function deleteEvent(
  eventId: string,
  scope: "series" | "occurrence",
  occurrence?: string,
): Promise<void> {
  const q = new URLSearchParams({ scope });
  if (occurrence) q.set("occurrence", occurrence);
  const res = await fetch(`${BASE}/events/${eventId}?${q}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`delete failed ${res.status}`);
}
