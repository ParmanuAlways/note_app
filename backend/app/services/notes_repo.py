"""Markdown note storage with git version history (FR-38/39).

Each note is a `<id>.md` file inside a per-owner git repository. Every create
or edit is a commit, so the full history is recoverable (AC-17) — there is no
cloud safety net on AFNET, so this local history is mandatory. The DB row holds
metadata + path; the body and its history live here in git.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from git import Repo

from app.config import get_settings


def _repo(owner_id: str) -> tuple[Repo, Path]:
    # Absolute path so GitPython resolves entries against the repo root, not cwd.
    path = (Path(get_settings().storage_root) / owner_id / "notes").resolve()
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists():
        repo = Repo.init(path)
        # Local committer identity so commits work with no global git config
        # (important on a locked-down air-gapped box).
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "AI Notes")
            cw.set_value("user", "email", "notes@local")
    else:
        repo = Repo(path)
    return repo, path


def _rel(note_id: str) -> str:
    return f"{note_id}.md"


def write(owner_id: str, note_id: str, content: str, message: str) -> str:
    """Write the note body and commit it. Returns the stored path."""
    repo, path = _repo(owner_id)
    file = path / _rel(note_id)
    file.write_text(content)
    repo.index.add([_rel(note_id)])  # path relative to the repo working tree
    repo.index.commit(message)
    return str(file)


def read(owner_id: str, note_id: str) -> str:
    _, path = _repo(owner_id)
    file = path / _rel(note_id)
    return file.read_text() if file.exists() else ""


def versions(owner_id: str, note_id: str) -> list[dict]:
    """Commit history for one note, newest first (FR-39)."""
    repo, _ = _repo(owner_id)
    return [
        {
            "sha": c.hexsha,
            "message": c.message.strip(),
            "at": datetime.fromtimestamp(c.committed_date),
        }
        for c in repo.iter_commits(paths=_rel(note_id))
    ]


def read_version(owner_id: str, note_id: str, sha: str) -> str:
    """The note body as it was at a specific commit (AC-17 history view)."""
    repo, _ = _repo(owner_id)
    try:
        return repo.git.show(f"{sha}:{_rel(note_id)}")
    except Exception as exc:  # noqa: BLE001
        raise KeyError(sha) from exc
