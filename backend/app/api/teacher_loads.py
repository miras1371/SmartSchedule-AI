from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.curriculum_subject import CurriculumSubject
from backend.app.models.teacher import Teacher
from backend.app.models.teacher_load import TeacherLoad
from backend.app.services.teacher_assignment_service import (
    get_assigned_hours,
    validate_weekly_load,
)


router = APIRouter(
    prefix="/teacher-loads",
    tags=["Teacher Loads"],
)


class TeacherLoadRequest(BaseModel):
    teacher_id: int = Field(gt=0)
    curriculum_subject_id: int = Field(gt=0)
    lecture_hours: int = Field(default=0, ge=0)
    practice_hours: int = Field(default=0, ge=0)
    lab_hours: int = Field(default=0, ge=0)
    lecture_per_week: int = Field(default=0, ge=0)
    practice_per_week: int = Field(default=0, ge=0)
    lab_per_week: int = Field(default=0, ge=0)
    lecture_max_students: int = Field(default=70, gt=0)
    practice_max_students: int | None = Field(default=None, gt=0)
    lab_max_students: int | None = Field(default=None, gt=0)
    language: str = Field(default="Русский", min_length=1, max_length=50)


def _load_response(load: TeacherLoad) -> dict:
    return {
        "id": load.id,
        "teacher_id": load.teacher_id,
        "curriculum_subject_id": load.curriculum_subject_id,
        "load": {
            "lecture_hours": load.lecture_hours,
            "practice_hours": load.practice_hours,
            "lab_hours": load.lab_hours,
            "lecture_per_week": load.lecture_per_week,
            "practice_per_week": load.practice_per_week,
            "lab_per_week": load.lab_per_week,
            "lecture_max_students": load.lecture_max_students,
            "practice_max_students": load.practice_max_students,
            "lab_max_students": load.lab_max_students,
            "language": load.language,
        },
    }


def _validate_references(
    db: Session,
    teacher_id: int,
    curriculum_subject_id: int,
) -> None:
    if db.query(Teacher).filter(Teacher.id == teacher_id).first() is None:
        raise HTTPException(
            status_code=404,
            detail="Преподаватель не найден.",
        )

    if (
        db.query(CurriculumSubject)
        .filter(CurriculumSubject.id == curriculum_subject_id)
        .first()
        is None
    ):
        raise HTTPException(
            status_code=404,
            detail="Предмет учебного плана не найден.",
        )


def _apply_request(load: TeacherLoad, request: TeacherLoadRequest) -> None:
    for field_name, value in request.model_dump().items():
        setattr(load, field_name, value)


@router.post("/")
def create_teacher_load(
    request: TeacherLoadRequest,
    db: Session = Depends(get_db),
):
    _validate_references(
        db,
        request.teacher_id,
        request.curriculum_subject_id,
    )

    duplicate = (
        db.query(TeacherLoad)
        .filter(
            TeacherLoad.teacher_id == request.teacher_id,
            TeacherLoad.curriculum_subject_id
            == request.curriculum_subject_id,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail="Для этого преподавателя и предмета нагрузка уже существует.",
        )

    load = TeacherLoad()
    _apply_request(load, request)
    db.add(load)
    db.flush()

    try:
        validate_weekly_load(load)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(error))

    db.commit()
    db.refresh(load)
    return {
        "message": "Нагрузка преподавателя успешно создана.",
        "teacher_load": _load_response(load),
    }


@router.put("/{load_id}")
def update_teacher_load(
    load_id: int,
    request: TeacherLoadRequest,
    db: Session = Depends(get_db),
):
    load = (
        db.query(TeacherLoad)
        .filter(TeacherLoad.id == load_id)
        .first()
    )
    if load is None:
        raise HTTPException(
            status_code=404,
            detail="Нагрузка преподавателя не найдена.",
        )

    _validate_references(
        db,
        request.teacher_id,
        request.curriculum_subject_id,
    )

    duplicate = (
        db.query(TeacherLoad)
        .filter(
            TeacherLoad.id != load_id,
            TeacherLoad.teacher_id == request.teacher_id,
            TeacherLoad.curriculum_subject_id
            == request.curriculum_subject_id,
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail="Для этого преподавателя и предмета нагрузка уже существует.",
        )

    assigned = get_assigned_hours(db=db, teacher_load_id=load.id)
    requested_hours = {
        "lecture_hours": request.lecture_hours,
        "practice_hours": request.practice_hours,
        "lab_hours": request.lab_hours,
    }
    for load_field, value in assigned.items():
        if requested_hours[load_field] < value:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Нельзя уменьшить {load_field} нагрузку ниже "
                    f"уже назначенных {value} часов."
                ),
            )

    _apply_request(load, request)
    try:
        validate_weekly_load(load)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(error))

    db.commit()
    db.refresh(load)
    return {
        "message": "Нагрузка преподавателя успешно обновлена.",
        "teacher_load": _load_response(load),
    }


@router.get("/")
def get_teacher_loads(
    db: Session = Depends(get_db),
):
    teacher_loads = (
        db.query(TeacherLoad)
        .order_by(TeacherLoad.id)
        .all()
    )

    result = []

    for load in teacher_loads:
        assigned = get_assigned_hours(
            db=db,
            teacher_load_id=load.id,
        )

        result.append(
            {
                "id": load.id,
                "teacher_id": load.teacher_id,
                "curriculum_subject_id": (
                    load.curriculum_subject_id
                ),
                "load": {
                    "lecture_hours": load.lecture_hours,
                    "practice_hours": load.practice_hours,
                    "lab_hours": load.lab_hours,
                    "lecture_per_week": load.lecture_per_week,
                    "practice_per_week": load.practice_per_week,
                    "lab_per_week": load.lab_per_week,
                    "lecture_max_students": (
                        load.lecture_max_students
                    ),
                    "practice_max_students": (
                        load.practice_max_students
                    ),
                    "lab_max_students": load.lab_max_students,
                    "language": load.language,
                },
                "allocated": assigned,
                "remaining": {
                    "lecture_hours": (
                        load.lecture_hours
                        - assigned["lecture_hours"]
                    ),
                    "practice_hours": (
                        load.practice_hours
                        - assigned["practice_hours"]
                    ),
                    "lab_hours": (
                        load.lab_hours
                        - assigned["lab_hours"]
                    ),
                },
            }
        )

    return {
        "count": len(result),
        "teacher_loads": result,
    }


@router.delete("/{load_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher_load(load_id: int, db: Session = Depends(get_db)):
    load = db.query(TeacherLoad).filter(TeacherLoad.id == load_id).first()
    if load is None:
        raise HTTPException(status_code=404, detail="Нагрузка преподавателя не найдена.")
    if load.assignments:
        raise HTTPException(
            status_code=409,
            detail=(
                "У нагрузки есть назначенные занятия. Повторите удаление "
                "с параметром remove_assignments=true, чтобы удалить назначения "
                "и связанные занятия из расписаний."
            ),
        )
    db.delete(load)
    db.commit()


@router.delete(
    "/{load_id}/with-assignments",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_teacher_load_with_assignments(
    load_id: int,
    db: Session = Depends(get_db),
):
    load = db.query(TeacherLoad).filter(TeacherLoad.id == load_id).first()
    if load is None:
        raise HTTPException(status_code=404, detail="Нагрузка преподавателя не найдена.")

    assignment_ids = {assignment.id for assignment in load.assignments}
    affected_lessons = {
        target.lesson
        for assignment in load.assignments
        for target in assignment.lesson_targets
        if target.lesson is not None
    }

    # A common lesson may contain targets from several teacher assignments.
    # Delete the whole lesson only when every target belongs to this load;
    # otherwise the assignment cascade removes only this load's targets.
    for lesson in affected_lessons:
        if all(
            target.teacher_assignment_id in assignment_ids
            for target in lesson.targets
        ):
            db.delete(lesson)

    db.delete(load)
    db.commit()
