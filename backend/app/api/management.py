from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.academic_period import AcademicPeriod
from backend.app.models.subject import Subject
from backend.app.models.scheduling_constraint import SchedulingConstraint
from backend.app.models.curriculum import Curriculum
from backend.app.models.curriculum_subject import CurriculumSubject
from backend.app.models.specialty import Specialty
from backend.app.models.lecture_stream import LectureStream
from backend.app.models.lecture_stream_group import LectureStreamGroup
from backend.app.models.group import Group


router = APIRouter(tags=["Management"])


class SubjectPayload(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)


class PeriodPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    academic_year: str = Field(min_length=4, max_length=20)
    semester: int = Field(ge=1, le=2)
    start_date: date
    end_date: date
    weeks: int = Field(gt=0, le=60)


class CurriculumPayload(BaseModel):
    specialty_id: int = Field(gt=0)
    academic_period_id: int = Field(gt=0)
    course: int = Field(ge=1, le=10)
    semester: int = Field(ge=1, le=2)
    academic_year: str = Field(min_length=4, max_length=20)


class CurriculumSubjectPayload(BaseModel):
    subject_id: int = Field(gt=0)
    hours: int = Field(gt=0)
    lecture_hours: int = Field(default=0, ge=0)
    practice_hours: int = Field(default=0, ge=0)
    lab_hours: int = Field(default=0, ge=0)
    lecture_per_week: int = Field(default=0, ge=0)
    practice_per_week: int = Field(default=0, ge=0)
    lab_per_week: int = Field(default=0, ge=0)
    lecture_max_students: int = Field(default=70, gt=0)
    practice_max_students: int | None = Field(default=None, gt=0)
    lab_max_students: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_hour_breakdown(self):
        component_hours = (
            self.lecture_hours + self.practice_hours + self.lab_hours
        )
        if component_hours != self.hours:
            raise ValueError(
                "Общее количество часов должно быть равно сумме "
                "лекций, практик и лабораторных."
            )
        if (
            self.lecture_per_week
            + self.practice_per_week
            + self.lab_per_week
            <= 0
        ):
            raise ValueError(
                "Укажите хотя бы одно еженедельное занятие."
            )
        return self


class StreamPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    specialty_id: int = Field(gt=0)
    academic_period_id: int = Field(gt=0)
    group_ids: list[int] = Field(default_factory=list)


def _subject(item: Subject) -> dict:
    return {"id": item.id, "code": item.code, "name": item.name}


def _period(item: AcademicPeriod) -> dict:
    return {
        "id": item.id, "name": item.name, "academic_year": item.academic_year,
        "semester": item.semester, "start_date": item.start_date,
        "end_date": item.end_date, "weeks": item.weeks,
    }


def _curriculum(item: Curriculum) -> dict:
    return {
        "id": item.id, "curriculum_id": item.id, "specialty_id": item.specialty_id,
        "specialty": item.specialty.code if item.specialty else None,
        "academic_period_id": item.academic_period_id,
        "academic_period_name": item.academic_period.name if item.academic_period else None,
        "course": item.course, "semester": item.semester,
        "academic_year": item.academic_year, "subjects_count": len(item.subjects),
    }


def _curriculum_subject(item: CurriculumSubject) -> dict:
    return {
        "id": item.id,
        "curriculum_id": item.curriculum_id,
        "subject_id": item.subject_id,
        "subject_code": item.subject.code if item.subject else None,
        "subject": item.subject.name if item.subject else None,
        "hours": item.hours,
        "lecture_hours": item.lecture_hours,
        "practice_hours": item.practice_hours,
        "lab_hours": item.lab_hours,
        "lecture_per_week": item.lecture_per_week,
        "practice_per_week": item.practice_per_week,
        "lab_per_week": item.lab_per_week,
        "lecture_max_students": item.lecture_max_students,
        "practice_max_students": item.practice_max_students,
        "lab_max_students": item.lab_max_students,
        "teacher_loads_count": len(item.teacher_loads),
    }


def _get_curriculum_subject(
    db: Session,
    curriculum_id: int,
    curriculum_subject_id: int,
) -> CurriculumSubject:
    item = db.get(CurriculumSubject, curriculum_subject_id)
    if item is None or item.curriculum_id != curriculum_id:
        raise HTTPException(
            status_code=404,
            detail="Дисциплина учебного плана не найдена.",
        )
    return item


def _stream(item: LectureStream) -> dict:
    return {
        "id": item.id, "name": item.name, "specialty_id": item.specialty_id,
        "academic_period_id": item.academic_period_id, "is_active": item.is_active,
        "group_ids": [link.group_id for link in item.groups],
        "group_names": [link.group.name for link in item.groups if link.group],
    }


@router.post("/subjects", status_code=status.HTTP_201_CREATED)
def create_subject(data: SubjectPayload, db: Session = Depends(get_db)):
    item = Subject(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Код предмета уже используется.") from error
    db.refresh(item)
    return {"subject": _subject(item)}


@router.patch("/subjects/{subject_id}")
def update_subject(subject_id: int, data: SubjectPayload, db: Session = Depends(get_db)):
    item = db.get(Subject, subject_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Предмет не найден.")
    item.code, item.name = data.code, data.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Код предмета уже используется.") from error
    db.refresh(item)
    return {"subject": _subject(item)}


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    item = db.get(Subject, subject_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Предмет не найден.")
    if item.curriculum_subjects:
        raise HTTPException(status_code=409, detail="Нельзя удалить предмет, включённый в учебный план. Сначала удалите его из учебных планов.")
    db.delete(item)
    db.commit()


@router.post("/periods", status_code=status.HTTP_201_CREATED)
def create_period(data: PeriodPayload, db: Session = Depends(get_db)):
    if data.end_date <= data.start_date:
        raise HTTPException(status_code=400, detail="Дата окончания должна быть позже даты начала.")
    item = AcademicPeriod(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"period": _period(item)}


@router.patch("/periods/{period_id}")
def update_period(period_id: int, data: PeriodPayload, db: Session = Depends(get_db)):
    item = db.get(AcademicPeriod, period_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Учебный период не найден.")
    if data.end_date <= data.start_date:
        raise HTTPException(status_code=400, detail="Дата окончания должна быть позже даты начала.")
    for field, value in data.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return {"period": _period(item)}


@router.delete("/periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period(period_id: int, db: Session = Depends(get_db)):
    item = db.get(AcademicPeriod, period_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Учебный период не найден.")
    if item.curricula:
        raise HTTPException(status_code=409, detail="Нельзя удалить период, связанный с учебными планами.")
    db.delete(item)
    db.commit()


@router.post("/curricula", status_code=status.HTTP_201_CREATED)
def create_curriculum(data: CurriculumPayload, db: Session = Depends(get_db)):
    if db.get(Specialty, data.specialty_id) is None or db.get(AcademicPeriod, data.academic_period_id) is None:
        raise HTTPException(status_code=404, detail="Специальность или учебный период не найдены.")
    item = Curriculum(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"curriculum": _curriculum(item)}


@router.patch("/curricula/{curriculum_id}")
def update_curriculum(curriculum_id: int, data: CurriculumPayload, db: Session = Depends(get_db)):
    item = db.get(Curriculum, curriculum_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Учебный план не найден.")
    if db.get(Specialty, data.specialty_id) is None or db.get(AcademicPeriod, data.academic_period_id) is None:
        raise HTTPException(status_code=404, detail="Специальность или учебный период не найдены.")
    for field, value in data.model_dump().items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return {"curriculum": _curriculum(item)}


@router.get("/curricula/{curriculum_id}/subjects")
def list_curriculum_subjects(
    curriculum_id: int,
    db: Session = Depends(get_db),
):
    curriculum = db.get(Curriculum, curriculum_id)
    if curriculum is None:
        raise HTTPException(status_code=404, detail="Учебный план не найден.")
    items = sorted(
        curriculum.subjects,
        key=lambda row: (
            row.subject.name.lower() if row.subject else "",
            row.id,
        ),
    )
    return {
        "curriculum": _curriculum(curriculum),
        "subjects": [_curriculum_subject(item) for item in items],
    }


@router.post(
    "/curricula/{curriculum_id}/subjects",
    status_code=status.HTTP_201_CREATED,
)
def create_curriculum_subject(
    curriculum_id: int,
    data: CurriculumSubjectPayload,
    db: Session = Depends(get_db),
):
    if db.get(Curriculum, curriculum_id) is None:
        raise HTTPException(status_code=404, detail="Учебный план не найден.")
    if db.get(Subject, data.subject_id) is None:
        raise HTTPException(status_code=404, detail="Предмет не найден.")
    item = CurriculumSubject(
        curriculum_id=curriculum_id,
        **data.model_dump(),
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Этот предмет уже включён в учебный план.",
        ) from error
    db.refresh(item)
    return {"curriculum_subject": _curriculum_subject(item)}


@router.patch(
    "/curricula/{curriculum_id}/subjects/{curriculum_subject_id}"
)
def update_curriculum_subject(
    curriculum_id: int,
    curriculum_subject_id: int,
    data: CurriculumSubjectPayload,
    db: Session = Depends(get_db),
):
    item = _get_curriculum_subject(db, curriculum_id, curriculum_subject_id)
    if db.get(Subject, data.subject_id) is None:
        raise HTTPException(status_code=404, detail="Предмет не найден.")
    if item.teacher_loads and data.subject_id != item.subject_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "Нельзя заменить предмет, пока для него назначены нагрузки "
                "преподавателей. Сначала удалите соответствующие нагрузки."
            ),
        )
    allocated = {
        field: sum(getattr(load, field) for load in item.teacher_loads)
        for field in (
            "lecture_hours", "practice_hours", "lab_hours",
            "lecture_per_week", "practice_per_week", "lab_per_week",
        )
    }
    if any(getattr(data, field) < value for field, value in allocated.items()):
        raise HTTPException(
            status_code=409,
            detail=(
                "Новые часы меньше суммарной нагрузки преподавателей. "
                "Сначала скорректируйте нагрузки в разделе «Квалификации»."
            ),
        )
    for field, value in data.model_dump().items():
        setattr(item, field, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Этот предмет уже включён в учебный план.",
        ) from error
    db.refresh(item)
    return {"curriculum_subject": _curriculum_subject(item)}


@router.delete(
    "/curricula/{curriculum_id}/subjects/{curriculum_subject_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_curriculum_subject(
    curriculum_id: int,
    curriculum_subject_id: int,
    db: Session = Depends(get_db),
):
    item = _get_curriculum_subject(db, curriculum_id, curriculum_subject_id)
    if item.teacher_loads:
        raise HTTPException(
            status_code=409,
            detail=(
                "Нельзя удалить дисциплину: для неё назначены нагрузки "
                "преподавателей. Удалите их в разделе «Квалификации»."
            ),
        )
    db.delete(item)
    db.commit()


@router.delete("/curricula/{curriculum_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_curriculum(curriculum_id: int, db: Session = Depends(get_db)):
    item = db.get(Curriculum, curriculum_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Учебный план не найден.")
    if item.subjects:
        raise HTTPException(status_code=409, detail="Сначала удалите предметы из учебного плана.")
    db.delete(item)
    db.commit()


@router.post("/lecture-streams", status_code=status.HTTP_201_CREATED)
def create_stream(data: StreamPayload, db: Session = Depends(get_db)):
    if db.get(Specialty, data.specialty_id) is None or db.get(AcademicPeriod, data.academic_period_id) is None:
        raise HTTPException(status_code=404, detail="Специальность или учебный период не найдены.")
    groups = db.query(Group).filter(Group.id.in_(data.group_ids)).all() if data.group_ids else []
    if len(groups) != len(set(data.group_ids)):
        raise HTTPException(status_code=404, detail="Одна из групп не найдена.")
    item = LectureStream(name=data.name, specialty_id=data.specialty_id, academic_period_id=data.academic_period_id)
    db.add(item)
    db.flush()
    db.add_all([LectureStreamGroup(lecture_stream_id=item.id, group_id=group.id) for group in groups])
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Такой лекционный поток уже существует.") from error
    db.refresh(item)
    return {"lecture_stream": _stream(item)}


@router.patch("/lecture-streams/{stream_id}")
def update_stream(stream_id: int, data: StreamPayload, db: Session = Depends(get_db)):
    item = db.get(LectureStream, stream_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Лекционный поток не найден.")
    if db.get(Specialty, data.specialty_id) is None or db.get(AcademicPeriod, data.academic_period_id) is None:
        raise HTTPException(status_code=404, detail="Специальность или учебный период не найдены.")
    groups = db.query(Group).filter(Group.id.in_(data.group_ids)).all() if data.group_ids else []
    if len(groups) != len(set(data.group_ids)):
        raise HTTPException(status_code=404, detail="Одна из групп не найдена.")
    item.name, item.specialty_id, item.academic_period_id = data.name, data.specialty_id, data.academic_period_id
    item.groups.clear()
    item.groups.extend(LectureStreamGroup(group_id=group.id) for group in groups)
    db.commit()
    db.refresh(item)
    return {"lecture_stream": _stream(item)}


@router.delete("/lecture-streams/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stream(stream_id: int, db: Session = Depends(get_db)):
    item = db.get(LectureStream, stream_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Лекционный поток не найден.")
    if item.lecture_parts or item.students:
        raise HTTPException(status_code=409, detail="Нельзя удалить поток, используемый в расписании или студентах.")
    db.delete(item)
    db.commit()


@router.patch("/constraints/{constraint_id}")
def update_constraint(constraint_id: int, data: dict, db: Session = Depends(get_db)):
    item = db.get(SchedulingConstraint, constraint_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ограничение не найдено.")
    allowed = {"constraint_type", "title", "description", "teacher_id", "classroom_id",
               "day_of_week", "start_time", "end_time", "is_active"}
    for field, value in data.items():
        if field in allowed:
            setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return {"constraint": {column.name: getattr(item, column.name) for column in SchedulingConstraint.__table__.columns}}


@router.delete("/constraints/{constraint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_constraint(constraint_id: int, db: Session = Depends(get_db)):
    item = db.get(SchedulingConstraint, constraint_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Ограничение не найдено.")
    db.delete(item)
    db.commit()
