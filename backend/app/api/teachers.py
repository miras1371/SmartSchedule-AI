from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.teacher import Teacher


router = APIRouter(prefix="/teachers", tags=["Teachers"])


class TeacherCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    position: str = Field(min_length=1, max_length=100)
    department: str = Field(min_length=1, max_length=255)
    email: str | None = None
    phone: str | None = None


class TeacherUpdate(TeacherCreate):
    pass


def teacher_response(teacher: Teacher) -> dict:
    return {
        "id": teacher.id,
        "full_name": teacher.full_name,
        "position": teacher.position,
        "department": teacher.department,
        "email": teacher.email,
        "phone": teacher.phone,
        "is_active": teacher.is_active,
    }


@router.post("", status_code=201)
def create_teacher(data: TeacherCreate, db: Session = Depends(get_db)):
    teacher = Teacher(**data.model_dump())
    db.add(teacher)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Преподаватель с таким email уже существует.")
    db.refresh(teacher)
    return {"teacher": teacher_response(teacher)}


@router.patch("/{teacher_id}")
def update_teacher(
    teacher_id: int,
    data: TeacherUpdate,
    db: Session = Depends(get_db),
):
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Преподаватель не найден.")
    if data.email and db.query(Teacher).filter(
        Teacher.email == data.email,
        Teacher.id != teacher_id,
    ).first() is not None:
        raise HTTPException(status_code=409, detail="Преподаватель с таким email уже существует.")
    for field, value in data.model_dump().items():
        setattr(teacher, field, value)
    db.commit()
    db.refresh(teacher)
    return {"teacher": teacher_response(teacher)}


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Преподаватель не найден.")
    if any(load.assignments for load in teacher.loads):
        raise HTTPException(
            status_code=409,
            detail="Нельзя удалить преподавателя с назначенной нагрузкой или занятиями.",
        )
    db.delete(teacher)
    db.commit()
