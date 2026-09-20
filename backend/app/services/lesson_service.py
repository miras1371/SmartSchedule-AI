from sqlalchemy.orm import Session

from backend.app.models.lesson import Lesson
from backend.app.models.lesson_target import LessonTarget
from backend.app.models.teacher_assignment import TeacherAssignment
from backend.app.models.subgroup_bundle import SubgroupBundle
from backend.app.models.subgroup_bundle_member import SubgroupBundleMember
from backend.app.services.subgroup_grouping_service import group_subgroups


LESSON_HOURS = 1


def _get_lesson_specs(
    assignment: TeacherAssignment,
) -> list[tuple[str, int]]:
    if assignment is None:
        raise ValueError(
            "Назначение преподавателя не найдено."
        )

    specs = [
        ("lecture", assignment.lecture_hours or 0),
        ("practice", assignment.practice_hours or 0),
        ("lab", assignment.lab_hours or 0),
    ]
    active_specs = [
        (lesson_type, hours)
        for lesson_type, hours in specs
        if hours > 0
    ]

    if not active_specs:
        raise ValueError(
            "TeacherAssignment не содержит учебных часов."
        )

    for lesson_type, _ in active_specs:
        if lesson_type == "lecture":
            expected_target_types = {
                "full_group",
                "lecture_part",
            }
        else:
            expected_target_types = {"subgroup"}

        if assignment.target_type not in expected_target_types:
            activity_name = {
                "lecture": "Лекция",
                "practice": "Практика",
                "lab": "Лабораторная работа",
            }[lesson_type]
            if lesson_type == "lecture":
                target_name = "полную группу или лекционную часть"
            else:
                target_name = "подгруппу"
            raise ValueError(
                f"{activity_name} должна быть назначена "
                f"на {target_name}."
            )

    return active_specs


def _validate_assignment_targets(
    assignment: TeacherAssignment,
) -> list:
    targets = list(assignment.targets)

    if not targets:
        raise ValueError(
            "У назначения преподавателя отсутствуют цели."
        )

    for target in targets:
        if target.target_type != assignment.target_type:
            raise ValueError(
                "Тип цели назначения не соответствует "
                "типу TeacherAssignment."
            )

        if target.target_type == "full_group":
            if target.group_id is None:
                raise ValueError(
                    "Цель full_group должна содержать group_id."
                )

            if target.subgroup_id is not None:
                raise ValueError(
                    "Цель full_group не должна содержать "
                    "subgroup_id."
                )

        elif target.target_type == "subgroup":
            if target.subgroup_id is None:
                raise ValueError(
                    "Цель subgroup должна содержать subgroup_id."
                )

            if target.group_id is not None:
                raise ValueError(
                    "Цель subgroup не должна содержать "
                    "group_id."
                )

        elif target.target_type == "lecture_part":
            if target.group_id is not None or target.subgroup_id is not None:
                raise ValueError(
                    "Цель lecture_part не должна содержать "
                    "group_id или subgroup_id."
                )
        elif target.target_type == "subgroup_bundle":
            if target.subgroup_bundle_id is None:
                raise ValueError(
                    "Цель subgroup_bundle должна содержать "
                    "subgroup_bundle_id."
                )
            if target.lecture_part_id is None:
                raise ValueError(
                    "Цель lecture_part должна содержать "
                    "lecture_part_id."
                )
        else:
            raise ValueError(
                "Обнаружен неизвестный тип цели назначения."
            )

    return targets


def _create_lesson_targets(
    db: Session,
    lesson: Lesson,
    assignment: TeacherAssignment,
    targets: list,
) -> None:
    subgroup_targets = [
        target for target in targets
        if target.target_type == "subgroup"
    ]
    other_targets = [
        target for target in targets
        if target.target_type != "subgroup"
    ]

    max_students = None
    if assignment.teacher_load is not None:
        if lesson.lesson_type == "practice":
            max_students = (
                assignment.teacher_load.practice_max_students
            )
        elif lesson.lesson_type == "lab":
            max_students = assignment.teacher_load.lab_max_students

    grouped_subgroups = group_subgroups(
        [target.subgroup for target in subgroup_targets],
        max_students,
    )

    for subgroup_group in grouped_subgroups:
        if len(subgroup_group) > 1:
            bundle = SubgroupBundle(
                lesson_id=lesson.id,
                student_count=sum(
                    subgroup.student_count
                    for subgroup in subgroup_group
                ),
            )
            db.add(bundle)
            db.flush()

            for subgroup in subgroup_group:
                db.add(
                    SubgroupBundleMember(
                        bundle_id=bundle.id,
                        subgroup_id=subgroup.id,
                    )
                )

            lesson.targets.append(
                LessonTarget(
                    target_type="subgroup_bundle",
                    subgroup_bundle_id=bundle.id,
                    teacher_assignment_id=assignment.id,
                )
            )
        else:
            subgroup = subgroup_group[0]
            lesson.targets.append(
                LessonTarget(
                    target_type="subgroup",
                    subgroup_id=subgroup.id,
                    teacher_assignment_id=assignment.id,
                )
            )

    for assignment_target in other_targets:
        if assignment_target.target_type == "full_group":
            lesson_target = LessonTarget(
                target_type="full_group",
                group_id=assignment_target.group_id,
                teacher_assignment_id=assignment.id,
            )

        elif assignment_target.target_type == "subgroup":
            lesson_target = LessonTarget(
                target_type="subgroup",
                subgroup_id=assignment_target.subgroup_id,
                teacher_assignment_id=assignment.id,
            )

        elif assignment_target.target_type == "lecture_part":
            lesson_target = LessonTarget(
                target_type="lecture_part",
                lecture_part_id=assignment_target.lecture_part_id,
                teacher_assignment_id=assignment.id,
            )
        else:
            raise ValueError(
                "Неизвестный target_type."
            )

        lesson.targets.append(lesson_target)


def create_lessons_for_assignment(
    db: Session,
    assignment: TeacherAssignment,
) -> list[Lesson]:
    targets = _validate_assignment_targets(
        assignment
    )

    lesson_specs = _get_lesson_specs(assignment)

    created_lessons: list[Lesson] = []

    for lesson_type, lessons_count in lesson_specs:
        for lesson_number in range(1, lessons_count + 1):
            lesson = Lesson(
                lesson_type=lesson_type,
                hours=LESSON_HOURS,
                lesson_number=lesson_number,
            )
            db.add(lesson)
            db.flush()

            _create_lesson_targets(
                db=db,
                lesson=lesson,
                assignment=assignment,
                targets=targets,
            )

            created_lessons.append(lesson)

    db.commit()

    for lesson in created_lessons:
        db.refresh(lesson)

    return created_lessons


def create_lessons_from_assignments(
    db: Session,
    assignments: list[TeacherAssignment],
) -> list[Lesson]:
    if not assignments:
        raise ValueError(
            "Необходимо передать хотя бы одно назначение преподавателя."
        )

    lesson_specs = []
    assignment_targets = []

    curriculum_subject_ids: set[int] = set()

    for assignment in assignments:
        targets = _validate_assignment_targets(
            assignment
        )
        specs = _get_lesson_specs(assignment)

        teacher_load = assignment.teacher_load

        if teacher_load is None:
            raise ValueError(
                f"Для назначения id={assignment.id} "
                "не найдено назначение нагрузки преподавателя."
            )

        if teacher_load.curriculum_subject_id is None:
            raise ValueError(
                f"Для назначения id={assignment.id} "
                "не указан curriculum_subject_id."
            )

        curriculum_subject_ids.add(
            teacher_load.curriculum_subject_id
        )

        lesson_specs.append(specs)

        assignment_targets.append(
            (
                assignment,
                targets,
            )
        )

    if len(curriculum_subject_ids) != 1:
        raise ValueError(
            "Нельзя объединить назначения преподавателей "
            "из разных учебных предметов."
        )

    if not lesson_specs:
        raise ValueError(
            "Не удалось определить тип общего занятия."
        )

    first_specs = lesson_specs[0]

    if any(specs != first_specs for specs in lesson_specs[1:]):
        raise ValueError(
            "Все назначения одного общего занятия должны "
            "иметь одинаковые типы и количество занятий."
        )

    all_target_keys: set[tuple[str, int]] = set()

    for assignment, targets in assignment_targets:
        for target in targets:
            if target.target_type == "full_group":
                target_key = (
                    "full_group",
                    target.group_id,
                )
            elif target.target_type == "subgroup":
                target_key = (
                    "subgroup",
                    target.subgroup_id,
                )
            else:
                target_key = (
                    "lecture_part",
                    target.lecture_part_id,
                )

            if target_key in all_target_keys:
                raise ValueError(
                    "Одна и та же группа или подгруппа "
                    "не может участвовать дважды "
                    "в одном общем занятии."
                )

            all_target_keys.add(target_key)

    created_lessons: list[Lesson] = []

    for lesson_type, lessons_count in first_specs:
        for lesson_number in range(1, lessons_count + 1):
            lesson = Lesson(
                lesson_type=lesson_type,
                hours=LESSON_HOURS,
                lesson_number=lesson_number,
            )
            db.add(lesson)
            db.flush()

            for assignment, targets in assignment_targets:
                _create_lesson_targets(
                    db=db,
                    lesson=lesson,
                    assignment=assignment,
                    targets=targets,
                )

            created_lessons.append(lesson)

    db.commit()

    for lesson in created_lessons:
        db.refresh(lesson)

    return created_lessons