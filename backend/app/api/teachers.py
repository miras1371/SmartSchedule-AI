from fastapi import APIRouter, Depends, HTTPException
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
    return {"teacher": {"id": teacher.id, "full_name": teacher.full_name, "position": teacher.position, "department": teacher.department, "email": teacher.email, "phone": teacher.phone, "is_active": teacher.is_active}}
