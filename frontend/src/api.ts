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

export interface ExtractionField {
  value: string | null;
  confidence: number;
  source_text: string | null;
  page: number | null;
  flags: string[];
}

export interface Extraction {
  id: string;
  document_id: string;
  version: number;
  fields: Record<string, ExtractionField>;
  model_used: string;
  confirmed: boolean;
  created_at: string;
}

export async function extractDocument(docId: string): Promise<Extraction> {
  const res = await fetch(`${BASE}/documents/${docId}/extract`, { method: "POST" });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || `extract failed ${res.status}`);
  }
  return res.json();
}

export interface ConfirmRequest {
  create: "event" | "task" | "none";
  event?: { title: string; starts_at: string; ends_at?: string | null; venue?: string | null; attendees?: string | null };
  task?: { title: string; due_at?: string | null; reply_by?: string | null };
  edited_fields?: Record<string, string | null>;
}

export async function confirmExtraction(id: string, payload: ConfirmRequest): Promise<{ confirmed: boolean; created_type: string | null; created_id: string | null }> {
  const res = await fetch(`${BASE}/extractions/${id}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`confirm failed ${res.status}`);
  return res.json();
}

export async function checkConflicts(start: string, end?: string): Promise<Occurrence[]> {
  const q = new URLSearchParams({ start });
  if (end) q.set("end", end);
  const res = await fetch(`${BASE}/events/conflicts?${q}`);
  if (!res.ok) throw new Error(`conflicts ${res.status}`);
  return res.json();
}

export interface TrashItem {
  type: "event" | "task" | "note" | "document";
  id: string;
  title: string;
  deleted_at: string;
}

export async function listTrash(): Promise<TrashItem[]> {
  const res = await fetch(`${BASE}/trash`);
  if (!res.ok) throw new Error(`trash ${res.status}`);
  return res.json();
}

export async function restoreItem(type: TrashItem["type"], id: string): Promise<void> {
  const res = await fetch(`${BASE}/${type}s/${id}/restore`, { method: "POST" });
  if (!res.ok) throw new Error(`restore failed ${res.status}`);
}

export interface NoteMeta {
  id: string;
  title: string;
  classification: string | null;
  created_at: string;
  updated_at: string;
  content: string;
}

export interface NoteVersion {
  sha: string;
  message: string;
  at: string;
}

export async function listNotes(): Promise<NoteMeta[]> {
  const res = await fetch(`${BASE}/notes`);
  if (!res.ok) throw new Error(`notes ${res.status}`);
  return res.json();
}

export async function getNote(id: string): Promise<NoteMeta> {
  const res = await fetch(`${BASE}/notes/${id}`);
  if (!res.ok) throw new Error(`note ${res.status}`);
  return res.json();
}

export async function createNote(input: { title: string; content: string }): Promise<NoteMeta> {
  const res = await fetch(`${BASE}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`create note failed ${res.status}`);
  return res.json();
}

export async function updateNote(id: string, input: { title?: string; content?: string }): Promise<NoteMeta> {
  const res = await fetch(`${BASE}/notes/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`update note failed ${res.status}`);
  return res.json();
}

export async function listNoteVersions(id: string): Promise<NoteVersion[]> {
  const res = await fetch(`${BASE}/notes/${id}/versions`);
  if (!res.ok) throw new Error(`versions ${res.status}`);
  return res.json();
}

export async function getNoteVersion(id: string, sha: string): Promise<{ sha: string; content: string }> {
  const res = await fetch(`${BASE}/notes/${id}/versions/${sha}`);
  if (!res.ok) throw new Error(`version ${res.status}`);
  return res.json();
}

export interface UploadItem {
  filename: string;
  status: "uploaded" | "duplicate" | "rejected";
  reason: string | null;
  document_id: string | null;
  duplicate_of: string | null;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  mime_type: string;
  page_count: number;
  reference_number: string | null;
  classification: string | null;
  created_at: string;
}

export async function uploadDocuments(files: File[], force = false): Promise<UploadItem[]> {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  const res = await fetch(`${BASE}/documents?force=${force}`, { method: "POST", body: fd });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `upload failed ${res.status}`);
  }
  return (await res.json()).items;
}

export async function listDocuments(): Promise<DocumentRecord[]> {
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error(`documents ${res.status}`);
  return res.json();
}

export const documentFileUrl = (id: string) => `${BASE}/documents/${id}/file`;

export interface Task {
  id: string;
  title: string;
  status: "open" | "done";
  due_at: string | null;
  reply_by: string | null;
}

export interface SuspenseItem extends Task {
  overdue: boolean;
}

export async function listTasks(status?: "open" | "done"): Promise<Task[]> {
  const q = status ? `?status=${status}` : "";
  const res = await fetch(`${BASE}/tasks${q}`);
  if (!res.ok) throw new Error(`tasks ${res.status}`);
  return res.json();
}

export async function listSuspense(): Promise<SuspenseItem[]> {
  const res = await fetch(`${BASE}/tasks/suspense`);
  if (!res.ok) throw new Error(`suspense ${res.status}`);
  return res.json();
}

export async function createTask(input: {
  title: string;
  due_at?: string | null;
  reply_by?: string | null;
}): Promise<Task> {
  const res = await fetch(`${BASE}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`create task failed ${res.status}`);
  return res.json();
}

export async function setTaskStatus(id: string, status: "open" | "done"): Promise<void> {
  const res = await fetch(`${BASE}/tasks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error(`update task failed ${res.status}`);
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
