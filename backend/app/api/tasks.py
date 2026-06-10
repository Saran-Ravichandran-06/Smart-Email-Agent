from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth.session import get_current_user
from app.database.session import get_db
from app.models.email import Email
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskResponse, TaskStatusUpdate
from app.services.task_extraction import VALID_TASK_STATUSES, sanitize_task_title, update_task_status

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by task status",
    ),
    email_id: int | None = Query(default=None, description="Filter by email id"),
) -> list[Task]:
    query = (
        db.query(Task)
        .join(Email, Task.email_id == Email.id)
        .filter(
            Email.user_id == user.id,
            Email.gmail_deleted_at.is_(None),
        )
        .options(joinedload(Task.email))
    )

    if status_filter is not None:
        normalized = status_filter.strip().lower()
        if normalized not in VALID_TASK_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Use one of: {', '.join(sorted(VALID_TASK_STATUSES))}",
            )
        query = query.filter(Task.status == normalized)

    if email_id is not None:
        query = query.filter(Task.email_id == email_id)

    raw_tasks = query.order_by(Task.created_at.desc()).all()
    tasks: list[Task] = []
    for task in raw_tasks:
        cleaned = sanitize_task_title(task.task_text)
        if cleaned:
            task.task_text = cleaned
            tasks.append(task)
    total_user_tasks = (
        db.query(Task.id)
        .join(Email, Task.email_id == Email.id)
        .filter(Email.user_id == user.id)
        .count()
    )
    print(
        "TASK API DB QUERY [list tasks]:",
        {
            "user_id": user.id,
            "status_filter": status_filter,
            "email_id": email_id,
            "task_ids": [task.id for task in tasks],
            "task_email_ids": [task.email_id for task in tasks],
            "visible_inbox_task_count": len(tasks),
            "total_user_task_count": total_user_tasks,
            "hidden_or_malformed_task_count": total_user_tasks - len(tasks),
        },
    )
    return tasks


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Task:
    task = (
        db.query(Task)
        .join(Email, Task.email_id == Email.id)
        .filter(
            Task.id == task_id,
            Email.user_id == user.id,
            Email.gmail_deleted_at.is_(None),
        )
        .first()
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    try:
        return update_task_status(db, task, payload.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
