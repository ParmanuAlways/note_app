"""Tasks API — status tracking (FR-22) + suspense/reply-by view (FR-23).

AI-free backbone: works with no GPU/models (NFR-9). Mirrors events.py.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.db.database import get_db
from app.db.models import AuditLog, Task, TaskStatus
from app.schemas.task import SuspenseItem, TaskCreate, TaskRead, TaskUpdate
from app.services import audit

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_owned(db: Session, owner_id: str, task_id: str, *, include_trashed: bool = False) -> Task:
    t = db.get(Task, task_id)
    if t is None or t.owner_id != owner_id:
        raise HTTPException(404, "task not found")
    if t.deleted_at is not None and not include_trashed:
        raise HTTPException(404, "task is in trash")
    return t


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Task:
    t = Task(owner_id=owner_id, **payload.model_dump())
    db.add(t)
    db.flush()
    audit.record(db, owner_id=owner_id, item_type="task", item_id=t.id, action="created", detail={"source": "manual"})
    db.commit()
    db.refresh(t)
    return t


@router.get("", response_model=list[TaskRead])
def list_tasks(
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
    status: TaskStatus | None = Query(None, description="filter by open/done"),
) -> list[Task]:
    stmt = select(Task).where(Task.owner_id == owner_id, Task.deleted_at.is_(None))
    if status is not None:
        stmt = stmt.where(Task.status == status)
    return list(db.scalars(stmt.order_by(Task.due_at.is_(None), Task.due_at)))


@router.get("/suspense", response_model=list[SuspenseItem])
def suspense(
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> list[SuspenseItem]:
    # Pending replies (FR-23): open tasks with a reply-by date, soonest first,
    # overdue flagged. A past reply-by is valid + overdue, never hidden (FR-11).
    now = datetime.now()
    stmt = select(Task).where(
        Task.owner_id == owner_id,
        Task.deleted_at.is_(None),
        Task.status == TaskStatus.open,
        Task.reply_by.is_not(None),
    ).order_by(Task.reply_by)
    out: list[SuspenseItem] = []
    for t in db.scalars(stmt):
        base = TaskRead.model_validate(t, from_attributes=True).model_dump()
        out.append(SuspenseItem(**base, overdue=t.reply_by is not None and t.reply_by < now))
    return out


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> Task:
    return _get_owned(db, owner_id, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Task:
    t = _get_owned(db, owner_id, task_id)
    changes = payload.model_dump(exclude_unset=True)
    completed = changes.get("status") == TaskStatus.done and t.status != TaskStatus.done
    for field, value in changes.items():
        setattr(t, field, value)
    audit.record(
        db, owner_id=owner_id, item_type="task", item_id=t.id,
        action="completed" if completed else "edited",
        detail={"fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{task_id}", status_code=204, response_class=Response)
def delete_task(task_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> Response:
    t = _get_owned(db, owner_id, task_id)
    t.deleted_at = datetime.now()
    audit.record(db, owner_id=owner_id, item_type="task", item_id=t.id, action="deleted")
    db.commit()
    return Response(status_code=204)


@router.post("/{task_id}/restore", response_model=TaskRead)
def restore_task(task_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> Task:
    t = _get_owned(db, owner_id, task_id, include_trashed=True)
    if t.deleted_at is None:
        raise HTTPException(400, "task is not in trash")
    t.deleted_at = None
    audit.record(db, owner_id=owner_id, item_type="task", item_id=t.id, action="restored")
    db.commit()
    db.refresh(t)
    return t


@router.get("/{task_id}/history")
def task_history(task_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> list[dict]:
    _get_owned(db, owner_id, task_id, include_trashed=True)
    stmt = select(AuditLog).where(
        AuditLog.owner_id == owner_id, AuditLog.item_type == "task", AuditLog.item_id == task_id
    ).order_by(AuditLog.at)
    return [{"at": a.at, "action": a.action, "detail": a.detail} for a in db.scalars(stmt)]
