from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.classroom import Classroom


router = APIRouter(
    prefix="/classrooms",
    tags=["Classrooms"],
)


class ClassroomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    capacity: int = Field(gt=0)
    room_type: str = Field(min_length=1, max_length=30)
    equipment: str | None = Field(default=None, max_length=255)


class ClassroomUpdate(ClassroomCreate):
    pass


@router.post("")
def create_classroom(
    classroom_data: ClassroomCreate,
    db: Session = Depends(get_db),
):
    existing_classroom = (
        db.query(Classroom)
        .filter(Classroom.name == classroom_data.name)
        .first()
    )

    if existing_classroom is not None:
        raise HTTPException(
            status_code=409,
            detail="Аудитория с таким названием уже существует.",
        )

    classroom = Classroom(
        name=classroom_data.name,
        capacity=classroom_data.capacity,
        room_type=classroom_data.room_type,
        equipment=classroom_data.equipment,
        is_active=True,
    )

    db.add(classroom)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Не удалось создать аудиторию.",
        )

    db.refresh(classroom)

    return {
        "message": "Аудитория успешно создана.",
        "classroom": {
            "id": classroom.id,
            "name": classroom.name,
            "capacity": classroom.capacity,
            "room_type": classroom.room_type,
            "equipment": classroom.equipment,
            "is_active": classroom.is_active,
        },
    }


@router.get("")
def get_classrooms(
    db: Session = Depends(get_db),
):
    classrooms = (
        db.query(Classroom)
        .order_by(Classroom.name)
        .all()
    )

    return {
        "count": len(classrooms),
        "classrooms": [
            {
                "id": classroom.id,
                "name": classroom.name,
                "capacity": classroom.capacity,
                "room_type": classroom.room_type,
                "equipment": classroom.equipment,
                "is_active": classroom.is_active,
            }
            for classroom in classrooms
        ],
    }


@router.patch("/{classroom_id}")
def update_classroom(
    classroom_id: int,
    classroom_data: ClassroomUpdate,
    db: Session = Depends(get_db),
):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Аудитория не найдена.")
    duplicate = db.query(Classroom).filter(
        Classroom.name == classroom_data.name,
        Classroom.id != classroom_id,
    ).first()
    if duplicate is not None:
        raise HTTPException(status_code=400, detail="Аудитория с таким названием уже существует.")
    classroom.name = classroom_data.name
    classroom.capacity = classroom_data.capacity
    classroom.room_type = classroom_data.room_type
    classroom.equipment = classroom_data.equipment
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Не удалось изменить аудиторию.")
    db.refresh(classroom)
    return {"message": "Аудитория успешно изменена.", "classroom": {
        "id": classroom.id, "name": classroom.name, "capacity": classroom.capacity,
        "room_type": classroom.room_type, "equipment": classroom.equipment,
        "is_active": classroom.is_active,
    }}


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(classroom_id: int, db: Session = Depends(get_db)):
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if classroom is None:
        raise HTTPException(status_code=404, detail="Аудитория не найдена.")
    if classroom.lesson_targets or classroom.schedule_assignments:
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить аудиторию, используемую в расписании.",
        )
    db.delete(classroom)
    db.commit()
