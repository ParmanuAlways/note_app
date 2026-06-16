# Requirements Document
## AI Notes & Scheduling Application (v1)

---

## 1. Purpose

A web application for an individual professional user that removes the friction between *receiving/capturing work information* and *acting on it*. The user uploads an official letter (or types/speaks a note); local AI extracts the meeting or task details; the user confirms; the item lands on an internal calendar, linked to its source, and is searchable in plain language.

**Core loop:** Capture (document or note) → AI extracts → User confirms/edits → Saved to internal calendar + notes → Linked and searchable.

---

## 2. Environment & Constraints

1. Runs entirely on **AFNET**. No public internet. No data leaves the network.
2. **No external calendar sync** (Google/Outlook/Apple impossible by design). The application maintains its own internal calendar.
3. All AI models run **locally on the server**. No cloud APIs anywhere.
4. Models sit behind a **swappable inference layer** — no model name hardcoded anywhere; dev/prod hardware or model changes must not require code rework.
5. Data is stored **on a server, keyed per user in the schema**. Scope is **single-user** for v1; the schema carries owner/unit fields so future multi-user (v2) is an extension, not a rewrite.
6. **Accuracy over latency.** Document extraction taking seconds to tens of seconds is acceptable. A wrong calendar entry is not.
7. Development hardware: GPU-equipped server (80GB-class card available for dev). Production hardware decided at deployment; the swappable inference layer (item 4) is the insurance.

---

## 3. Technology Stack (locked)

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | React (web app, browser client) |
| Auth | Keycloak (authentication only in v1) |
| AI — document extraction | Local vision-language model (Qwen2.5-VL class), quantized as hardware requires |
| AI — voice transcription | Local Whisper |
| AI — semantic search | Local embedding model |
| Notes storage | Plain-text / Markdown files, per-user keyed |
| Structured data | Server database (events, tasks, links, audit, metadata) |
| Document storage | Original uploaded files retained on server |

---

## 4. Functional Requirements

### 4.1 Capture

- **FR-1** User can upload a scanned letter, PDF, or image. **Accepted formats: PDF, JPG, PNG, TIFF. Limits: max 50 MB per file, max 20 files per batch** (configurable). Out-of-bounds uploads are rejected with a clear message — limits are stated, never discovered by crash. **Multi-page documents are fully supported:** all pages are processed and extraction fields may come from any page or enclosure.
- **FR-2** **Batch upload:** multiple files can be uploaded at once; they are processed sequentially with a visible queue and per-file status (queued / processing / ready to confirm / failed).
- **FR-3** **Duplicate detection (two-stage):** at upload, the file hash is checked against existing documents; after extraction, the reference number is checked at the confirm stage. A likely duplicate prompts the user — "this appears to match an existing document: open it, or proceed anyway?" — rather than silently creating a copy.
- **FR-4** Scan-quality check on upload, with a defined mechanism: minimum resolution/DPI floor plus a model-based legibility probe (the VLM is asked whether it can read the page; below-threshold → reject). Unreadable files are rejected with a clear re-upload prompt — never processed into guesses.
- **FR-5** User can capture a quick note by typing.
- **FR-6** User can capture a note by voice; transcription runs locally (Whisper); the transcript is editable before anything is extracted or saved. **Max recording length: 5 minutes (configurable). The audio file is retained alongside the transcript** (same record-keeping principle as documents).
- **FR-7** **Manual entry:** the user can create an event or task directly by hand — no document, no AI extraction — through a standard form (title, date/time, venue, etc.). The AI loop is the headline path, not the only path.

### 4.2 AI Extraction

- **FR-8** A local vision-language model reads the uploaded document (all pages) and extracts: subject, date, time, venue, attendee names, reference number, deadline/action, and **reply-by / suspense date** where present.
- **FR-9** **Full-text retention for search:** the complete text the model reads from the document is stored alongside the structured fields, so keyword and semantic search cover the entire letter body — not just the extracted fields.
- **FR-10** Extraction output is **structured (JSON fields) with per-field confidence**.
- **FR-11** Validation layer checks extracted values, with rules per date type: a **meeting date** in the past is flagged as implausible; a **reply-by/suspense date** in the past is valid and marked **overdue** (it feeds the pending-replies view, FR-23) — never rejected. Dates must be real calendar dates; missing or implausible fields are left blank and flagged — **never invented**.
- **FR-12** For typed/spoken notes, the model extracts task + date/time references (absolute and relative — "tomorrow", "next Friday") and offers to schedule.
- **FR-13** Notes with no schedulable content are stored gracefully as plain notes (no error, no forced event).

### 4.3 Confirm Step (load-bearing)

- **FR-14** Every extraction passes through a **confirm/edit screen** before saving: all extracted fields shown, low-confidence fields visually flagged, user can edit, add, or dismiss. Nothing is auto-saved to the calendar without user confirmation. **Dismiss discards only the proposed event/task — the uploaded document itself is always kept**, filed and searchable (the original is the record, FR-27).
- **FR-14a** **Re-extraction on demand:** any stored document can be re-run through extraction at any time (e.g. after a failed/poor first pass or a model upgrade per NFR-7). The new result goes through the same confirm screen; the previous extraction is versioned, not overwritten.
- **FR-15** **Conflict warning:** if the meeting being confirmed overlaps an existing calendar event, the confirm screen shows the clash before the user saves.

### 4.4 Internal Calendar & Events

- **FR-16** Self-contained event store. This application *is* the calendar for these items.
- **FR-17** Events carry: title, date/time, venue, attendee names (as text metadata — no invites are sent; single-user), link to source note/document, reminders, classification tag.
- **FR-18** **Event lifecycle:** any event can be **edited, rescheduled, or deleted** after creation. Reschedules and deletions are recorded in the audit trail; the link to the source document is preserved through changes.
- **FR-19** **Trash / soft delete:** deleted events, notes, and documents go to a restorable trash, purged after a configurable period (default 30 days). No direct hard delete from the UI — the timed purge from trash is the only permanent-removal path. In a records context, accidental permanent loss is unacceptable.
- **FR-20** **Recurring events:** an event can repeat (daily / weekly / monthly / yearly, with an end date or count). Editing a recurring event offers "this occurrence" vs "entire series."
- **FR-21** Time-zone aware (single zone acceptable in v1).

### 4.5 Tasks & Suspense Tracking

- **FR-22** **Task status:** extracted/created tasks carry a status (**open / done**), can be marked done from the timeline or dashboard, and completed tasks are visually distinct and filterable out.
- **FR-23** **Suspense / pending-replies view:** letters with a reply-by date appear in a dedicated pending-actions view, sorted by due date, with overdue items flagged. Marking the reply done clears the item (audit-logged).

### 4.6 Linking

- **FR-24** **Hard auto-links (deterministic):** documents sharing the same reference number are linked automatically via exact/normalized string matching. The AI *extracts* the reference; plain string logic *matches* it. The model never decides a hard link.
- **FR-25** **Soft suggestions (AI):** semantically similar notes are surfaced via local embeddings as *suggestions only* — user confirms; never auto-applied.
- **FR-26** Every event links back to the note/document it came from; opening an event shows its source.

### 4.7 Source & Record Integrity

- **FR-27** The **original uploaded document is retained** and openable from any linked note/event. The extraction is metadata attached to the original — the original is the record.
- **FR-28** **Audit trail:** document uploaded, fields extracted, fields edited by user, event created/edited/rescheduled/deleted/restored from trash, task status changes, note edits — all logged with timestamp. **The trail is viewable per item:** any event, note, or document offers a "history" view showing its changes in order. A log that exists but cannot be read satisfies nothing.

### 4.8 Search & Ask

- **FR-29** **Ask about schedule:** natural-language questions ("what meetings next week", "what's due Friday") are answered **exactly from the calendar database**. The model translates the question into a structured query; the answer comes from the DB — never from model recall of text.
- **FR-30** **Ask about content (find):** natural-language search retrieves and displays the relevant notes/documents. v1 *finds and shows*; it does not write AI-generated summaries (deferred to v1.1).
- **FR-31** Keyword search and semantic search (local embeddings) across all notes, events, and **full document text** (per FR-9).
- **FR-32** A **query router** sits in front: classifies each question as schedule-type → DB query, or content-type → retrieval. The content branch is built to accommodate v1.1 RAG without rework.

### 4.9 Organisation & Display

- **FR-33** **Today dashboard (landing screen):** on login the user sees today's events, open tasks, items awaiting confirmation, and upcoming/overdue suspense dates — one glance answers "what do I need to do today."
- **FR-34** **Unified timeline:** notes and scheduled items in one chronological view, with tap-through to source.
- **FR-35** **Calendar views:** the internal calendar is viewable by **day, week, month, and year**, with standard navigation (previous/next, jump to today, jump to a date). Day and week views show events at their time slots; month and year views show density/presence with drill-down to the day. Clicking any event from any view opens its details and source link.
- **FR-36** **Classification tag** (e.g. Restricted / Confidential): a searchable, filterable label on any item. **Findability only — explicitly not an access control** (single-user scope makes this safe; see §7 limitation note).

### 4.10 Notifications

- **FR-37** Reminders delivered via **browser notifications** (permission flow handled in-app). Known limitation: fires only when the browser is running and permission granted; the timeline/dashboard is the backstop for anything missed. Notifications are a convenience layer; the dashboard is the source of truth.

### 4.11 Storage

- **FR-38** Notes stored as plain-text/Markdown, per-user keyed in the schema. **Notes are editable after creation;** every edit is captured in version history (FR-39) and the audit trail.
- **FR-39** Automated local backup and version history (git-style) on AFNET — there is no cloud safety net; this is mandatory.

### 4.12 Authentication

- **FR-40** Login via Keycloak. v1 needs authentication only; roles/permissions (authorization) are deferred to v2.

### 4.13 System Administration

- **FR-41** **System status page:** model loaded (yes/no), GPU and disk usage, processing-queue depth, last successful backup time. On a self-managed air-gapped server with no vendor monitoring, this page is the first-line diagnostic when extraction stops working.

---

## 5. Non-Functional Requirements

- **NFR-1 Accuracy over latency** — extraction in seconds-to-tens-of-seconds is acceptable; correctness is the bar.
- **NFR-2 No data loss** — capture must never lose a note, recording, or upload, including on processing failure; failed batch items remain in the queue for retry.
- **NFR-3 Privacy** — nothing leaves AFNET; no external calls of any kind. This must be literally true and verifiable.
- **NFR-4 Date/time accuracy is the single highest risk** — local models misread dates more than anything else. Mitigations are mandatory: structured output (FR-10), validation (FR-11), and the confirm step (FR-14).
- **NFR-5 Date format convention** — all date display and parsing follows **DD MMM YYYY** (e.g. 09 Jun 2026), consistent with service correspondence. No US MM/DD formats anywhere in UI, parsing, or storage display. This single convention prevents the 03/06 vs 06/03 class of error.
- **NFR-6 Single resident pipeline is sufficient** — single-user scope; batch uploads queue sequentially; no concurrent-request serving required in v1.
- **NFR-7 Model-swap safety** — switching extraction/transcription/embedding models is a configuration change, not a code change.
- **NFR-8 Use maintained components for the calendar UI** — calendar views (FR-35) should use an established offline-bundlable React calendar library, not hand-rolled date grids.
- **NFR-9 Degraded mode when inference is down** — if the model/inference layer is unavailable, the application keeps working without it: manual entry (FR-7), calendar views, keyword search, viewing notes/documents, and task management all remain functional. Uploads and voice notes are accepted into the queue and processed when inference returns. The status page (FR-41) reflects the state. The app must never white-screen because the GPU did.

---

## 6. Deferred Scope

### v1.1
- **AI report/summary generation** (RAG): model-written summaries of notes — with **mandatory citations to source notes** and draft-review before use. Held out of v1 for hallucination risk.
- **Correction feedback loop:** log user edits to extractions as future fine-tuning data.
- **Export/print:** notes and schedules to PDF/paper.

### v2 — Unit / shared workspace
- Multi-user unit pool: members add items; shared read and edit access.
- Roles & permissions (authorization); **classification upgraded from tag to access control** (mandatory once others can see items).
- Concurrent-edit handling; original-document immutability rules; unit administration.
- v1 schema already carries owner/unit fields so v2 extends rather than rewrites.

---

## 7. Known Limitations (recorded deliberately)

1. Classification tag is **not** a security control in v1 — it organises and filters only. This is safe solely because the scope is single-user. v2 must revisit.
2. Browser notifications are **not guaranteed delivery** — browser must be open with permission granted. Dashboard/timeline is the backstop.
3. Extraction quality depends on scan quality and the locally hostable model; plausible-but-wrong reads (e.g. "3rd" as "8th") can pass validation — the confirm step (FR-14) is the final catch and depends on the user reviewing.
4. Attendee names are text metadata only — no directory resolution, no invites (by design in single-user scope).
5. Batch processing is sequential — a large batch takes proportionally long; the queue status (FR-2) makes this visible rather than fast.
6. Duplicate detection (FR-3) catches identical files and matching reference numbers; a re-scan of the same letter at different quality may evade the hash check and rely on the reference match.

---

## 8. Acceptance Criteria (v1 demo bar)

1. A real **multi-page** scanned letter is uploaded → extraction returns structured fields with confidence, including a reply-by date found on a later page.
2. A deliberately wrong/low-confidence date is **visibly flagged and corrected** at the confirm screen.
3. A meeting that clashes with an existing event triggers the **conflict warning** at confirm.
4. The confirmed meeting appears on the dashboard, the timeline, and in **day/week/month/year calendar views**, with all dates displayed DD MMM YYYY.
5. An event or task is created **manually** (no document, no AI) through the form.
6. The event is **rescheduled and then deleted**; it appears in **trash** and is **restored**; all actions appear in the audit trail; the source link survives.
7. A recurring weekly event is created and a single occurrence edited without altering the series.
8. Opening any event opens the **original letter**.
9. Two letters sharing a reference number are **auto-linked**; uploading the **same file again** triggers the duplicate prompt.
10. A keyword that appears only in the **body** of a letter (not in any extracted field) is found by search.
11. A letter with a reply-by date appears in the **pending-replies view** and clears when marked done.
12. "What's on next week?" returns the correct answer **from the database**.
13. A voice note is captured, transcribed, edited, and scheduled through the same confirm flow.
14. A batch of three letters uploads with visible queue status and all three reach confirm.
15. The **system status page** shows model state, queue depth, and last backup.
16. With **inference stopped**, manual entry, calendar, keyword search, and viewing still work; a queued upload processes once inference restarts.
17. A note is **edited after creation** and its **history view** shows both versions.
18. An oversized file is rejected with a clear limit message, not an error crash.
19. An extraction is **dismissed** at confirm — the document remains stored and searchable; the same document is then **re-extracted** and reaches confirm again.
20. A letter with a reply-by date **already in the past** is accepted, marked overdue, and appears flagged in the pending-replies view.
21. Network monitoring confirms **zero external calls**.
