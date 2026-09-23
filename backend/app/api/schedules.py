from uuid import uuid4

import logging
from multiprocessing import Process

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.core.dependencies import get_db
from backend.app.models.academic_period import AcademicPeriod
from backend.app.models.generation_job import GenerationJob
from backend.app.models.schedule_item import ScheduleItem
from backend.app.models.schedule_version import ScheduleVersion
from backend.app.models.classroom import Classroom
from backend.app.models.time_slot import TimeSlot
from backend.app.scheduler.data_loader import load_scheduling_data
from backend.app.scheduler.scheduler import ScheduleGenerator, generate_schedule
from backend.app.services.schedule_validation_service import (
    validate_schedule_version,
)


router = APIRouter(prefix="/schedules", tags=["Schedules"])
logger = logging.getLogger(__name__)


class ScheduleGenerateRequest(BaseModel):
    academic_period_id: int = Field(gt=0)


class ScheduleVersionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = None


def _run_generation_job(job_id: str, academic_period_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return

        job.status = "running"
        db.commit()

        version = generate_schedule(
            db=db,
            academic_period_id=academic_period_id,
        )
        job.status = "generated"
        job.schedule_version_id = version.id
        job.error = None
        db.commit()
    except ValueError as error:
        db.rollback()
        logger.warning("Schedule generation failed for job %s: %s", job_id, error)
        _mark_generation_failed(db, job_id, str(error))
    except Exception as error:
        db.rollback()
        logger.exception("Unexpected schedule generation failure for job %s", job_id)
        _mark_generation_failed(
            db,
            job_id,
            f"Внутренняя ошибка генерации: {error}",
        )
    finally:
        db.close()


def _mark_generation_failed(
    db: Session,
    job_id: str,
    error: str,
) -> None:
    job = db.get(GenerationJob, job_id)
    if job is None:
        return
    job.status = "failed"
    job.error = error
    db.commit()


def _generation_job_response(job: GenerationJob) -> dict:
    return {
        "job_id": job.id,
        "academic_period_id": job.academic_period_id,
        "status": job.status,
        "version_id": job.schedule_version_id,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _version_response(version: ScheduleVersion) -> dict:
    return {
        "id": version.id,
        "academic_period_id": version.academic_period_id,
        "academic_period_name": (
            version.academic_period.name if version.academic_period else None
        ),
        "version_number": version.version_number,
        "name": version.name,
        "status": version.status,
        "created_at": version.created_at,
        "items_count": len(version.schedule_items),
    }


def _target_response(target, classroom) -> dict:
    group_pairs = {
        (student.student.group_id, student.student.group.name)
        for student in (
            list(target.subgroup.students)
            if target.subgroup is not None
            else list(target.lecture_part.students)
            if target.lecture_part is not None
            else [
                student
                for member in target.subgroup_bundle.members
                for student in member.subgroup.students
            ]
            if target.subgroup_bundle is not None
            else []
        )
    }
    if target.group is not None:
        group_pairs.add((target.group.id, target.group.name))

    result = {
        "id": target.id,
        "target_type": target.target_type,
        "group_id": target.group_id,
        "group_name": target.group.name if target.group else None,
        "subgroup_id": target.subgroup_id,
        "subgroup_name": target.subgroup.name if target.subgroup else None,
        "lecture_part_id": target.lecture_part_id,
        "lecture_part_name": target.lecture_part.name if target.lecture_part else None,
        "subgroup_bundle_id": target.subgroup_bundle_id,
        "group_ids": [group_id for group_id, _ in sorted(group_pairs)],
        "group_names": [group_name for _, group_name in sorted(group_pairs)],
        "classroom": (
            {
                "id": classroom.id,
                "name": classroom.name,
                "capacity": classroom.capacity,
                "room_type": classroom.room_type,
            }
            if classroom
            else None
        ),
    }

    if target.subgroup_bundle:
        result["subgroup_bundle"] = {
            "student_count": target.subgroup_bundle.student_count,
            "subgroup_ids": [
                member.subgroup_id for member in target.subgroup_bundle.members
            ],
        }
    return result


def _item_response(item: ScheduleItem) -> dict:
    lesson = item.lesson
    classrooms_by_target = {
        assignment.lesson_target_id: assignment.classroom
        for assignment in item.classroom_assignments
    }
    first_target = lesson.targets[0] if lesson.targets else None
    assignment = first_target.teacher_assignment if first_target else None
    teacher = (
        assignment.teacher_load.teacher
        if assignment and assignment.teacher_load
        else None
    )
    subject = (
        assignment.teacher_load.curriculum_subject.subject
        if assignment
        and assignment.teacher_load
        and assignment.teacher_load.curriculum_subject
        else None
    )
    return {
        "id": item.id,
        "lesson_id": lesson.id,
        "lesson_type": lesson.lesson_type,
        "hours": lesson.hours,
        "lesson_number": lesson.lesson_number,
        "time_slot": {
            "id": item.time_slot.id,
            "day_of_week": item.time_slot.day_of_week,
            "lesson_number": item.time_slot.lesson_number,
            "start_time": item.time_slot.start_time,
            "end_time": item.time_slot.end_time,
        },
        "teacher": (
            {"id": teacher.id, "full_name": teacher.full_name}
            if teacher
            else None
        ),
        "subject": (
            {"id": subject.id, "code": subject.code, "name": subject.name}
            if subject
            else None
        ),
        "targets": [
            _target_response(
                target,
                classrooms_by_target.get(target.id),
            )
            for target in lesson.targets
        ],
    }


def _target_group_ids(target) -> set[int]:
    group_ids: set[int] = set()
    if target.group is not None:
        group_ids.add(target.group.id)
    if target.subgroup is not None:
        group_ids.update(student.student.group_id for student in target.subgroup.students)
    if target.lecture_part is not None:
        group_ids.update(student.student.group_id for student in target.lecture_part.students)
    if target.subgroup_bundle is not None:
        for member in target.subgroup_bundle.members:
            group_ids.update(student.student.group_id for student in member.subgroup.students)
    return group_ids


@router.get("/versions")
def get_schedule_versions(
    academic_period_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    query = db.query(ScheduleVersion).order_by(
        ScheduleVersion.academic_period_id,
        ScheduleVersion.version_number.desc(),
    )
    if academic_period_id is not None:
        query = query.filter(ScheduleVersion.academic_period_id == academic_period_id)
    versions = query.all()
    return {
        "count": len(versions),
        "versions": [_version_response(version) for version in versions],
    }


@router.get("/versions/active")
def get_active_schedule_versions(
    academic_period_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    query = db.query(ScheduleVersion).filter(
        ScheduleVersion.status == "published"
    )
    if academic_period_id is not None:
        query = query.filter(ScheduleVersion.academic_period_id == academic_period_id)

    versions = query.order_by(
        ScheduleVersion.academic_period_id,
        ScheduleVersion.version_number.desc(),
    ).all()

    return {
        "count": len(versions),
        "versions": [_version_response(version) for version in versions],
    }


@router.post("/generate", status_code=202)
def generate_schedule_version(
    request: ScheduleGenerateRequest,
    db: Session = Depends(get_db),
):
    if db.query(AcademicPeriod.id).filter(
        AcademicPeriod.id == request.academic_period_id
    ).first() is None:
        raise HTTPException(status_code=404, detail="Учебный период не найден.")

    job = GenerationJob(
        id=str(uuid4()),
        academic_period_id=request.academic_period_id,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if "uq_generation_jobs_active_period" in str(error.orig):
            raise HTTPException(
                status_code=409,
                detail="Для этого учебного периода генерация уже выполняется.",
            ) from error
        raise

    try:
        process = Process(
            target=_run_generation_job,
            args=(job.id, request.academic_period_id),
            daemon=True,
        )
        process.start()
    except Exception as error:
        _mark_generation_failed(db, job.id, f"Не удалось запустить генерацию: {error}")
        raise HTTPException(
            status_code=500,
            detail="Не удалось запустить отдельный процесс генерации.",
        ) from error
    return {
        "message": "Генерация расписания поставлена в очередь.",
        "job": _generation_job_response(job),
    }


@router.get("/generation/{job_id}")
def get_generation_status(job_id: str, db: Session = Depends(get_db)):
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задача генерации не найдена.")
    return {"job": _generation_job_response(job)}


@router.get("/diagnostics/{academic_period_id}")
def diagnose_schedule_period(
    academic_period_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    try:
        generator = ScheduleGenerator(db, academic_period_id)
        generator.data = load_scheduling_data(db, academic_period_id)
        generator._prepare_indexes()
        generator._validate_input_data()
    except ValueError as error:
        return {
            "academic_period_id": academic_period_id,
            "valid": False,
            "error": str(error),
            "issues": [str(error)],
        }
    return {
        "academic_period_id": academic_period_id,
        "valid": True,
        "lessons_count": len(generator.data.lessons),
        "time_slots_count": len(generator.data.time_slots),
        "classrooms_count": len(generator.data.classrooms),
    }


@router.get("/classroom-map")
def get_classroom_map(
    version_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    """Return the selected schedule version in a classroom-oriented shape."""
    version_query = db.query(ScheduleVersion)
    if version_id is not None:
        version = version_query.filter(ScheduleVersion.id == version_id).first()
    else:
        version = (
            version_query.filter(ScheduleVersion.status == "published")
            .order_by(ScheduleVersion.created_at.desc())
            .first()
            or version_query.order_by(ScheduleVersion.created_at.desc()).first()
        )
    if version is None:
        raise HTTPException(status_code=404, detail="Нет доступной версии расписания.")

    schedule = get_schedule(version.id, None, None, None, db)
    classrooms = db.query(Classroom).order_by(Classroom.name).all()
    slots = (
        db.query(TimeSlot)
        .filter(TimeSlot.is_active.is_(True))
        .order_by(TimeSlot.day_of_week, TimeSlot.lesson_number)
        .all()
    )
    classroom_items: dict[int, dict[tuple[int, int], dict]] = {
        classroom.id: {} for classroom in classrooms
    }
    for item in schedule["items"]:
        for target in item["targets"]:
            classroom = target.get("classroom")
            if classroom is None or classroom["id"] not in classroom_items:
                continue
            key = (item["time_slot"]["day_of_week"], item["time_slot"]["lesson_number"])
            entry = classroom_items[classroom["id"]].setdefault(
                key,
                {
                    "lesson_id": item["lesson_id"],
                    "subject": item["subject"],
                    "lesson_type": item["lesson_type"],
                    "teacher": item["teacher"],
                    "time_slot": item["time_slot"],
                    "group_names": set(),
                    "subgroup_names": set(),
                },
            )
            entry["group_names"].update(target.get("group_names") or [])
            if target.get("subgroup_name"):
                entry["subgroup_names"].add(target["subgroup_name"])

    result_classrooms = []
    for classroom in classrooms:
        activities = [
            {
                **entry,
                "group_names": sorted(entry["group_names"]),
                "subgroup_names": sorted(entry["subgroup_names"]),
            }
            for entry in classroom_items[classroom.id].values()
        ]
        activities.sort(
            key=lambda item: (
                item["time_slot"]["day_of_week"],
                item["time_slot"]["lesson_number"],
            )
        )
        result_classrooms.append(
            {
                "id": classroom.id,
                "name": classroom.name,
                "capacity": classroom.capacity,
                "room_type": classroom.room_type,
                "equipment": classroom.equipment,
                "activities": activities,
            }
        )
    return {
        "version": schedule["version"],
        "time_slots": [
            {
                "id": slot.id,
                "day_of_week": slot.day_of_week,
                "lesson_number": slot.lesson_number,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
            }
            for slot in slots
        ],
        "classrooms": result_classrooms,
    }


@router.patch("/{version_id}")
def update_schedule_version(
    version_id: int,
    request: ScheduleVersionUpdateRequest,
    db: Session = Depends(get_db),
):
    version = db.get(ScheduleVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Версия расписания не найдена.")

    if request.name is not None:
        version.name = request.name

    if request.status is not None:
        allowed_statuses = {"draft", "generated", "published", "archived", "failed"}
        if request.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Недопустимый статус версии: {request.status}",
            )
        if request.status == "published":
            validation = validate_schedule_version(db=db, version_id=version_id)
            if not validation["valid"]:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Нельзя опубликовать невалидную версию.",
                        "validation": validation,
                    },
                )
            db.query(ScheduleVersion).filter(
                ScheduleVersion.academic_period_id == version.academic_period_id,
                ScheduleVersion.status == "published",
                ScheduleVersion.id != version.id,
            ).update(
                {ScheduleVersion.status: "archived"},
                synchronize_session=False,
            )
        if request.status == "archived" and version.status == "published":
            raise HTTPException(
                status_code=409,
                detail="Сначала опубликуйте другую версию, затем архивируйте текущую.",
            )
        version.status = request.status

    db.commit()
    db.refresh(version)
    return {"version": _version_response(version)}


@router.post("/{version_id}/publish")
def publish_schedule_version(
    version_id: int,
    db: Session = Depends(get_db),
):
    version = db.get(ScheduleVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Версия расписания не найдена.")

    if version.status == "archived":
        raise HTTPException(
            status_code=409,
            detail="Архивную версию нельзя опубликовать.",
        )

    validation = validate_schedule_version(db=db, version_id=version_id)
    if not validation["valid"]:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Нельзя опубликовать невалидную версию.",
                "validation": validation,
            },
        )

    db.query(ScheduleVersion).filter(
        ScheduleVersion.academic_period_id == version.academic_period_id,
        ScheduleVersion.status == "published",
    ).update({ScheduleVersion.status: "archived"}, synchronize_session=False)

    version.status = "published"
    db.commit()
    db.refresh(version)
    return {"version": _version_response(version)}


@router.post("/{version_id}/archive")
def archive_schedule_version(
    version_id: int,
    db: Session = Depends(get_db),
):
    version = db.get(ScheduleVersion, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Версия расписания не найдена.")

    if version.status == "published":
        raise HTTPException(
            status_code=409,
            detail="Сначала опубликуйте другую версию, затем архивируйте текущую.",
        )

    version.status = "archived"
    db.commit()
    db.refresh(version)
    return {"version": _version_response(version)}


@router.get("/{version_id}")
def get_schedule(
    version_id: int,
    group_id: int | None = Query(default=None, gt=0),
    teacher_id: int | None = Query(default=None, gt=0),
    classroom_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    version = db.query(ScheduleVersion).filter(ScheduleVersion.id == version_id).first()
    if version is None:
        raise HTTPException(status_code=404, detail="Версия расписания не найдена.")

    items = []
    for item in version.schedule_items:
        targets = item.lesson.targets
        if group_id is not None and group_id not in {
            group for target in targets for group in _target_group_ids(target)
        }:
            continue
        if teacher_id is not None and not any(
            target.teacher_assignment.teacher_load.teacher_id == teacher_id
            for target in targets
        ):
            continue
        if classroom_id is not None and not any(
            assignment.classroom_id == classroom_id
            for assignment in item.classroom_assignments
        ):
            continue
        items.append(_item_response(item))

    items.sort(
        key=lambda item: (
            item["time_slot"]["day_of_week"],
            item["time_slot"]["lesson_number"],
            item["lesson_id"],
        )
    )
    return {
        "version": {
            "id": version.id,
            "academic_period_id": version.academic_period_id,
            "version_number": version.version_number,
            "name": version.name,
            "status": version.status,
        },
        "count": len(items),
        "items": items,
    }


@router.get("/{version_id}/validate")
def validate_schedule(version_id: int, db: Session = Depends(get_db)):
    try:
        return validate_schedule_version(db=db, version_id=version_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{version_id}/groups/{group_id}")
def get_group_schedule(version_id: int, group_id: int, db: Session = Depends(get_db)):
    return get_schedule(version_id, group_id, None, None, db)


@router.get("/{version_id}/teachers/{teacher_id}")
def get_teacher_schedule(version_id: int, teacher_id: int, db: Session = Depends(get_db)):
    return get_schedule(version_id, None, teacher_id, None, db)


@router.get("/{version_id}/classrooms/{classroom_id}")
def get_classroom_schedule(version_id: int, classroom_id: int, db: Session = Depends(get_db)):
    return get_schedule(version_id, None, None, classroom_id, db)


@router.get("/{version_id}/calendar")
def get_schedule_calendar(version_id: int, db: Session = Depends(get_db)):
    schedule = get_schedule(version_id, None, None, None, db)
    days: dict[int, list[dict]] = {}
    for item in schedule["items"]:
        days.setdefault(item["time_slot"]["day_of_week"], []).append(item)
    return {
        "version": schedule["version"],
        "days": [
            {"day_of_week": day, "items": days[day]} for day in sorted(days)
        ],
    }
