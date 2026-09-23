from collections import defaultdict

from sqlalchemy.orm import Session

from backend.app.models.schedule_version import ScheduleVersion


def _target_student_ids(target) -> set[int]:
    if target.group is not None:
        return {student.id for student in target.group.students}
    if target.subgroup is not None:
        return {student.student_id for student in target.subgroup.students}
    if target.lecture_part is not None:
        return {student.student_id for student in target.lecture_part.students}
    if target.subgroup_bundle is not None:
        return {
            student.student_id
            for member in target.subgroup_bundle.members
            for student in member.subgroup.students
        }
    return set()


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
    slot_students: dict[int, dict[int, int]] = defaultdict(dict)
    slot_classrooms: dict[int, dict[int, int]] = defaultdict(dict)
    student_day_lessons: dict[tuple[int, int], set[int]] = defaultdict(set)
    lesson_occurrences: dict[int, int] = defaultdict(int)

    for item in version.schedule_items:
        lesson = item.lesson
        lesson_occurrences[lesson.id] += 1
        classrooms_by_target = {
            assignment.lesson_target_id: assignment.classroom
            for assignment in item.classroom_assignments
        }
        lecture_capacity = (
            sum(_target_student_count(target) for target in lesson.targets)
            if lesson.lesson_type == "lecture"
            else None
        )
        if lesson.lesson_type == "lecture":
            lecture_room_ids = {
                classroom.id
                for classroom in classrooms_by_target.values()
                if classroom is not None
            }
            if len(lecture_room_ids) > 1:
                issues.append({
                    "code": "lecture_classroom_mismatch",
                    "lesson_id": lesson.id,
                    "message": "Цели одной лекции назначены в разные аудитории.",
                })

        for target in lesson.targets:
            classroom = classrooms_by_target.get(target.id)
            if classroom is None:
                issues.append({
                    "code": "missing_classroom",
                    "lesson_id": lesson.id,
                    "target_id": target.id,
                    "message": "Для цели занятия не назначена аудитория.",
                })
                continue

            required_capacity = (
                lecture_capacity
                if lecture_capacity is not None
                else _target_student_count(target)
            )
            if classroom.capacity < required_capacity:
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

            for student_id in _target_student_ids(target):
                previous_lesson = slot_students[item.time_slot_id].get(
                    student_id
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
                            f"Студент #{student_id} также назначен на "
                            f"занятие {previous_lesson}."
                        ),
                    })
                slot_students[item.time_slot_id][student_id] = lesson.id
                student_day_lessons[
                    (student_id, item.time_slot.day_of_week)
                ].add(lesson.id)

    for lesson_id, occurrences in lesson_occurrences.items():
        if occurrences > 1:
            issues.append({
                "code": "duplicate_lesson",
                "lesson_id": lesson_id,
                "message": (
                    f"Занятие сохранено в версии {occurrences} раз."
                ),
            })

    for (student_id, day_of_week), lesson_ids in student_day_lessons.items():
        if len(lesson_ids) > 6:
            issues.append({
                "code": "student_daily_limit",
                "student_id": student_id,
                "day_of_week": day_of_week,
                "message": (
                    f"У студента #{student_id} в день {day_of_week} "
                    f"назначено {len(lesson_ids)} занятий при лимите 6."
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
