from collections import defaultdict

from sqlalchemy.orm import Session

from backend.app.models.schedule_version import ScheduleVersion


def _target_resources(target) -> set[tuple[str, int]]:
    resources: set[tuple[str, int]] = set()

    if target.group_id is not None:
        resources.add(("group", target.group_id))

    if target.subgroup is not None:
        resources.add(("subgroup", target.subgroup.id))
        resources.update(
            ("group", student.student.group_id)
            for student in target.subgroup.students
        )

    if target.lecture_part is not None:
        resources.add(("lecture_part", target.lecture_part.id))
        resources.update(
            ("group", student.student.group_id)
            for student in target.lecture_part.students
        )

    if target.subgroup_bundle is not None:
        resources.add(("subgroup_bundle", target.subgroup_bundle.id))
        for member in target.subgroup_bundle.members:
            resources.add(("subgroup", member.subgroup_id))
            resources.update(
                ("group", student.student.group_id)
                for student in member.subgroup.students
            )

    return resources


def validate_schedule_version(
    db: Session,
    version_id: int,
) -> dict:
    version = (
        db.query(ScheduleVersion)
        .filter(ScheduleVersion.id == version_id)
        .first()
    )

    if version is None:
        raise ValueError("Версия расписания не найдена.")

    issues: list[dict] = []
    slot_teachers: dict[int, dict[int, int]] = defaultdict(dict)
    slot_resources: dict[int, dict[tuple[str, int], int]] = defaultdict(dict)
    slot_classrooms: dict[int, dict[int, int]] = defaultdict(dict)
    lesson_occurrences: dict[int, int] = defaultdict(int)

    for item in version.schedule_items:
        lesson = item.lesson
        lesson_occurrences[lesson.id] += 1

        for target in lesson.targets:
            classroom = target.classroom
            if classroom is None:
                issues.append({
                    "code": "missing_classroom",
                    "lesson_id": lesson.id,
                    "target_id": target.id,
                    "message": "Для цели занятия не назначена аудитория.",
                })
                continue

            if classroom.capacity < _target_student_count(target):
                issues.append({
                    "code": "classroom_capacity",
                    "lesson_id": lesson.id,
                    "target_id": target.id,
                    "message": (
                        f"Аудитория {classroom.name} рассчитана на "
                        f"{classroom.capacity} студентов."
                    ),
                })

            if (
                lesson.lesson_type == "lab"
                and classroom.room_type != "computer_lab"
            ):
                issues.append({
                    "code": "invalid_lab_classroom",
                    "lesson_id": lesson.id,
                    "target_id": target.id,
                    "message": (
                        f"Лаборатория назначена в аудитории "
                        f"{classroom.name} не типа computer_lab."
                    ),
                })

            previous_lesson = slot_classrooms[item.time_slot_id].get(
                classroom.id
            )
            if previous_lesson is not None and previous_lesson != lesson.id:
                issues.append({
                    "code": "classroom_conflict",
                    "lesson_id": lesson.id,
                    "target_id": target.id,
                    "message": (
                        f"Аудитория {classroom.name} также используется "
                        f"занятием {previous_lesson} в этом слоте."
                    ),
                })
            slot_classrooms[item.time_slot_id][classroom.id] = lesson.id

            teacher = target.teacher_assignment.teacher_load.teacher
            if teacher is not None:
                previous_lesson = slot_teachers[item.time_slot_id].get(
                    teacher.id
                )
                if (
                    previous_lesson is not None
                    and previous_lesson != lesson.id
                ):
                    issues.append({
                        "code": "teacher_conflict",
                        "lesson_id": lesson.id,
                        "target_id": target.id,
                        "message": (
                            f"Преподаватель {teacher.full_name} также "
                            f"назначен на занятие {previous_lesson}."
                        ),
                    })
                slot_teachers[item.time_slot_id][teacher.id] = lesson.id

            for resource in _target_resources(target):
                previous_lesson = slot_resources[item.time_slot_id].get(
                    resource
                )
                if (
                    previous_lesson is not None
                    and previous_lesson != lesson.id
                ):
                    issues.append({
                        "code": "student_conflict",
                        "lesson_id": lesson.id,
                        "target_id": target.id,
                        "message": (
                            f"Ресурс {resource[0]}:{resource[1]} также "
                            f"занят на занятии {previous_lesson}."
                        ),
                    })
                slot_resources[item.time_slot_id][resource] = lesson.id

    for lesson_id, occurrences in lesson_occurrences.items():
        if occurrences > 1:
            issues.append({
                "code": "duplicate_lesson",
                "lesson_id": lesson_id,
                "message": (
                    f"Занятие сохранено в версии {occurrences} раз."
                ),
            })

    return {
        "valid": not issues,
        "version_id": version.id,
        "status": version.status,
        "items_count": len(version.schedule_items),
        "issues_count": len(issues),
        "issues": issues,
    }


def _target_student_count(target) -> int:
    if target.group is not None:
        return target.group.student_count
    if target.subgroup is not None:
        return target.subgroup.student_count
    if target.lecture_part is not None:
        return target.lecture_part.student_count
    if target.subgroup_bundle is not None:
        return target.subgroup_bundle.student_count
    return 0
