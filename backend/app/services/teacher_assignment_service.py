from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.group import Group
from backend.app.models.lecture_part import LecturePart
from backend.app.models.student import Student
from backend.app.models.subgroup import Subgroup
from backend.app.models.teacher_assignment import TeacherAssignment
from backend.app.models.teacher_assignment_target import TeacherAssignmentTarget
from backend.app.models.teacher_load import TeacherLoad


VALID_TARGET_TYPES = {
    "full_group",
    "subgroup",
    "lecture_part",
}


def validate_weekly_load(teacher_load: TeacherLoad) -> None:
    curriculum_subject = teacher_load.curriculum_subject

    if curriculum_subject is None:
        raise ValueError(
            "Для TeacherLoad не найден CurriculumSubject."
        )

    curriculum = curriculum_subject.curriculum
    if curriculum is None or curriculum.academic_period is None:
        raise ValueError(
            "Для CurriculumSubject не найден академический период."
        )

    weeks = curriculum.academic_period.weeks
    if weeks <= 0:
        raise ValueError(
            "Количество учебных недель должно быть больше нуля."
        )

    hour_pairs = (
        ("lecture", teacher_load.lecture_hours, teacher_load.lecture_per_week),
        ("practice", teacher_load.practice_hours, teacher_load.practice_per_week),
        ("lab", teacher_load.lab_hours, teacher_load.lab_per_week),
    )

    for label, semester_hours, weekly_hours in hour_pairs:
        if semester_hours < 0 or weekly_hours < 0:
            raise ValueError(
                f"{label}: часы не могут быть отрицательными."
            )

        expected_hours = weekly_hours * weeks
        if semester_hours != expected_hours:
            raise ValueError(
                f"{label}: семестровая нагрузка "
                f"{semester_hours} не равна недельной нагрузке "
                f"{weekly_hours} × {weeks} недель = {expected_hours}."
            )


def get_assigned_hours(db: Session, teacher_load_id: int) -> dict[str, int]:
    result = (
        db.query(
            func.coalesce(func.sum(TeacherAssignment.lecture_hours), 0),
            func.coalesce(func.sum(TeacherAssignment.practice_hours), 0),
            func.coalesce(func.sum(TeacherAssignment.lab_hours), 0),
        )
        .filter(
            TeacherAssignment.teacher_load_id == teacher_load_id
        )
        .first()
    )

    return {
        "lecture_hours": int(result[0]),
        "practice_hours": int(result[1]),
        "lab_hours": int(result[2]),
    }


def create_teacher_assignment(
    db: Session,
    teacher_load_id: int,
    target_type: str,
    targets: list[dict],
    lecture_hours: int = 0,
    practice_hours: int = 0,
    lab_hours: int = 0,
) -> TeacherAssignment:

    # =========================================================
    # 1. Базовая проверка входных данных
    # =========================================================

    if target_type not in VALID_TARGET_TYPES:
        raise ValueError(
            f"Недопустимый target_type: {target_type}."
        )

    if not targets:
        raise ValueError(
            "Необходимо указать хотя бы одну цель назначения."
        )

    if target_type == "full_group":
        target_ids = [target.get("group_id") for target in targets]
        target_name = "группа"
    elif target_type == "subgroup":
        target_ids = [target.get("subgroup_id") for target in targets]
        target_name = "подгруппа"
    else:
        target_ids = [target.get("lecture_part_id") for target in targets]
        target_name = "лекционная часть"

    if len(target_ids) != len(set(target_ids)):
        raise ValueError(
            f"Одна и та же {target_name} не может быть указана "
            "несколько раз в одном назначении."
        )

    if lecture_hours < 0:
        raise ValueError(
            "Количество лекционных часов не может быть отрицательным."
        )

    if practice_hours < 0:
        raise ValueError(
            "Количество практических часов не может быть отрицательным."
        )

    if lab_hours < 0:
        raise ValueError(
            "Количество лабораторных часов не может быть отрицательным."
        )

    total_hours = (
        lecture_hours
        + practice_hours
        + lab_hours
    )

    if total_hours <= 0:
        raise ValueError(
            "TeacherAssignment должен содержать хотя бы один учебный час."
        )

    # =========================================================
    # 2. Получаем TeacherLoad
    # =========================================================

    teacher_load = (
        db.query(TeacherLoad)
        .filter(
            TeacherLoad.id == teacher_load_id
        )
        .first()
    )

    if teacher_load is None:
        raise ValueError(
            "TeacherLoad не найден."
        )

    curriculum_subject = teacher_load.curriculum_subject

    if curriculum_subject is None:
        raise ValueError(
            "Для TeacherLoad не найден CurriculumSubject."
        )

    curriculum = curriculum_subject.curriculum

    if curriculum is None:
        raise ValueError(
            "Для CurriculumSubject не найден Curriculum."
        )

    validate_weekly_load(teacher_load)

    # =========================================================
    # 3. Проверяем соответствие типа назначения часам
    # =========================================================

    if target_type == "full_group":

        if practice_hours > 0 or lab_hours > 0:
            raise ValueError(
                "Для full_group нельзя назначать практические "
                "или лабораторные часы."
            )

        if lecture_hours <= 0:
            raise ValueError(
                "Для full_group должны быть указаны лекционные часы."
            )

    elif target_type == "subgroup":

        if lecture_hours > 0:
            raise ValueError(
                "Для subgroup нельзя назначать лекционные часы."
            )

        if practice_hours <= 0 and lab_hours <= 0:
            raise ValueError(
                "Для subgroup должны быть указаны практические "
                "или лабораторные часы."
            )

    elif target_type == "lecture_part":
        if practice_hours > 0 or lab_hours > 0:
            raise ValueError(
                "Для lecture_part нельзя назначать практические "
                "или лабораторные часы."
            )

        if lecture_hours <= 0:
            raise ValueError(
                "Для lecture_part должны быть указаны лекционные часы."
            )

    # =========================================================
    # 4. Проверяем соответствие часов TeacherLoad
    # =========================================================

    assigned_hours = get_assigned_hours(
        db,
        teacher_load_id,
    )

    remaining_lecture_hours = (
        teacher_load.lecture_per_week
        - assigned_hours["lecture_hours"]
    )

    remaining_practice_hours = (
        teacher_load.practice_per_week
        - assigned_hours["practice_hours"]
    )

    remaining_lab_hours = (
        teacher_load.lab_per_week
        - assigned_hours["lab_hours"]
    )

    if lecture_hours > remaining_lecture_hours:
        raise ValueError(
            "Количество назначаемых лекционных часов "
            "превышает доступную нагрузку преподавателя."
        )

    if practice_hours > remaining_practice_hours:
        raise ValueError(
            "Количество назначаемых практических часов "
            "превышает доступную нагрузку преподавателя."
        )

    if lab_hours > remaining_lab_hours:
        raise ValueError(
            "Количество назначаемых лабораторных часов "
            "превышает доступную нагрузку преподавателя."
        )

    # =========================================================
    # 5. Нормализуем и проверяем цели
    # =========================================================

    normalized_targets = []

    for target in targets:

        if target_type == "full_group":

            group_id = target.get("group_id")

            if group_id is None:
                raise ValueError(
                    "Для full_group необходимо указать group_id."
                )

            group = (
                db.query(Group)
                .filter(Group.id == group_id)
                .first()
            )

            if group is None:
                raise ValueError(
                    f"Группа с id={group_id} не найдена."
                )

            # -------------------------------------------------
            # Проверяем специальность
            # -------------------------------------------------

            if group.specialty_id != curriculum.specialty_id:
                raise ValueError(
                    f"Группа «{group.name}» относится к другой "
                    f"специальности и не может быть назначена "
                    f"на этот учебный план."
                )

            # -------------------------------------------------
            # Проверяем курс
            # -------------------------------------------------

            if group.course != curriculum.course:
                raise ValueError(
                    f"Группа «{group.name}» относится к "
                    f"{group.course} курсу, а учебный план "
                    f"предназначен для {curriculum.course} курса."
                )

            normalized_targets.append(
                {
                    "target_type": "full_group",
                    "group_id": group_id,
                    "subgroup_id": None,
                }
            )

        elif target_type == "subgroup":

            subgroup_id = target.get("subgroup_id")

            if subgroup_id is None:
                raise ValueError(
                    "Для subgroup необходимо указать subgroup_id."
                )

            subgroup = (
                db.query(Subgroup)
                .filter(Subgroup.id == subgroup_id)
                .first()
            )

            if subgroup is None:
                raise ValueError(
                    f"Подгруппа с id={subgroup_id} не найдена."
                )

            subgroup_set = subgroup.subgroup_set

            if subgroup_set is None:
                raise ValueError(
                    f"Для подгруппы id={subgroup_id} "
                    f"не найден набор подгрупп."
                )

            # -------------------------------------------------
            # Проверяем, что набор подгрупп активный
            # -------------------------------------------------

            if subgroup_set.status != "active":
                raise ValueError(
                    f"Подгруппа «{subgroup.name}» относится "
                    f"к неактивному набору подгрупп."
                )

            # -------------------------------------------------
            # Проверяем академический период
            # -------------------------------------------------

            if (
                subgroup_set.academic_period_id
                != curriculum.academic_period_id
            ):
                raise ValueError(
                    f"Подгруппа «{subgroup.name}» относится "
                    f"к другому академическому периоду."
                )

            # -------------------------------------------------
            # Проверяем специальность лекционного потока
            # -------------------------------------------------

            lecture_stream = subgroup_set.lecture_stream

            if lecture_stream is None:
                raise ValueError(
                    f"Для набора подгрупп id={subgroup_set.id} "
                    f"не найден лекционный поток."
                )

            if (
                lecture_stream.specialty_id
                != curriculum.specialty_id
            ):
                raise ValueError(
                    f"Подгруппа «{subgroup.name}» относится "
                    f"к другой специальности."
                )

            # -------------------------------------------------
            # Проверяем студентов подгруппы
            # -------------------------------------------------

            subgroup_students = list(subgroup.students)

            if not subgroup_students:
                raise ValueError(
                    f"Подгруппа «{subgroup.name}» не содержит студентов."
                )

            for subgroup_student in subgroup_students:

                student = subgroup_student.student

                if student is None:
                    raise ValueError(
                        f"Для подгруппы «{subgroup.name}» "
                        f"обнаружена некорректная запись студента."
                    )

                group = student.group

                if group is None:
                    raise ValueError(
                        f"Студент «{student.full_name}» "
                        f"не относится ни к одной группе."
                    )

                if group.specialty_id != curriculum.specialty_id:
                    raise ValueError(
                        f"Студент «{student.full_name}» находится "
                        f"в группе другой специальности."
                    )

                if group.course != curriculum.course:
                    raise ValueError(
                        f"Студент «{student.full_name}» находится "
                        f"в группе другого курса."
                    )

            normalized_targets.append(
                {
                    "target_type": "subgroup",
                    "group_id": None,
                    "subgroup_id": subgroup_id,
                }
            )

        elif target_type == "lecture_part":
            lecture_part_id = target.get("lecture_part_id")

            if lecture_part_id is None:
                raise ValueError(
                    "Для lecture_part необходимо указать lecture_part_id."
                )

            lecture_part = (
                db.query(LecturePart)
                .filter(LecturePart.id == lecture_part_id)
                .first()
            )

            if lecture_part is None:
                raise ValueError(
                    f"Лекционная часть с id={lecture_part_id} не найдена."
                )

            lecture_stream = lecture_part.lecture_stream
            if lecture_stream is None:
                raise ValueError(
                    f"Для лекционной части id={lecture_part_id} "
                    "не найден поток."
                )

            if lecture_stream.specialty_id != curriculum.specialty_id:
                raise ValueError(
                    "Лекционная часть относится к другой специальности."
                )

            if lecture_stream.academic_period_id != (
                curriculum.academic_period_id
            ):
                raise ValueError(
                    "Лекционная часть относится к другому "
                    "академическому периоду."
                )

            if not lecture_part.students:
                raise ValueError(
                    f"Лекционная часть «{lecture_part.name}» "
                    "не содержит студентов."
                )

            normalized_targets.append(
                {
                    "target_type": "lecture_part",
                    "group_id": None,
                    "subgroup_id": None,
                    "lecture_part_id": lecture_part_id,
                }
            )

        # =========================================================
        # 5.1. Проверяем повторное назначение тех же целей
        # =========================================================
        existing_targets = (
            db.query(TeacherAssignmentTarget)
            .join(
                TeacherAssignment,
                TeacherAssignment.id
                == TeacherAssignmentTarget.teacher_assignment_id,
            )
            .filter(
                TeacherAssignment.teacher_load_id == teacher_load_id,
                TeacherAssignment.target_type == target_type,
                TeacherAssignmentTarget.target_type == target_type,
            )
            .all()
        )

        if target_type == "full_group":
            existing_ids = {
                target.group_id
                for target in existing_targets
                if target.group_id is not None
            }

            for target in normalized_targets:
                if target["group_id"] in existing_ids:
                    raise ValueError(
                        f"Группа с id={target['group_id']} уже назначена "
                        "этому преподавателю по этому типу занятия."
                    )

        elif target_type == "subgroup":
            existing_ids = {
                target.subgroup_id
                for target in existing_targets
                if target.subgroup_id is not None
            }

            for target in normalized_targets:
                if target["subgroup_id"] in existing_ids:
                    raise ValueError(
                        f"Подгруппа с id={target['subgroup_id']} уже назначена "
                        "этому преподавателю по этому типу занятия."
                    )

        else:
            existing_ids = {
                target.lecture_part_id
                for target in existing_targets
                if target.lecture_part_id is not None
            }

            for target in normalized_targets:
                if target["lecture_part_id"] in existing_ids:
                    raise ValueError(
                        f"Лекционная часть с id="
                        f"{target['lecture_part_id']} уже назначена "
                        "этому преподавателю."
                    )

    # =========================================================
    # 6. Создаём TeacherAssignment
    # =========================================================

    first_target = normalized_targets[0]

    assignment = TeacherAssignment(
        teacher_load_id=teacher_load_id,
        target_type=target_type,
        group_id=first_target["group_id"],
        subgroup_id=first_target["subgroup_id"],
        lecture_part_id=first_target.get("lecture_part_id"),
        lecture_hours=lecture_hours,
        practice_hours=practice_hours,
        lab_hours=lab_hours,
    )

    db.add(assignment)
    db.flush()

    # =========================================================
    # 7. Создаём все TeacherAssignmentTarget
    # =========================================================

    for target in normalized_targets:

        assignment_target = TeacherAssignmentTarget(
            teacher_assignment_id=assignment.id,
            target_type=target["target_type"],
            group_id=target["group_id"],
            subgroup_id=target["subgroup_id"],
            lecture_part_id=target.get("lecture_part_id"),
        )

        db.add(assignment_target)

    # =========================================================
    # 8. Сохраняем
    # =========================================================

    db.commit()
    db.refresh(assignment)

    return assignment