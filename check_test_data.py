from sqlalchemy import func
from backend.app.core.database import SessionLocal

from backend.app.models import (
    AcademicPeriod,
    Specialty,
    Group,
    Student,
    LectureStream,
    LectureStreamStudent,
    SubgroupSet,
    Subgroup,
    SubgroupStudent,
    Subject,
    Curriculum,
    Teacher,
    TeacherLoad,
    TeacherAssignment,
    Lesson,
    Classroom,
)


def main():
    db = SessionLocal()

    try:
        prefix = "TEST400"

        print()
        print("=" * 80)
        print(f"ПРОВЕРКА ТЕСТОВОГО НАБОРА {prefix}")
        print("=" * 80)

        # ---------------------------------------------------------
        # 1. Общая статистика
        # ---------------------------------------------------------

        print()
        print("1. ОБЩАЯ СТАТИСТИКА")
        print("-" * 80)

        academic_periods = (
            db.query(AcademicPeriod)
            .filter(AcademicPeriod.name.like(f"{prefix}%"))
            .all()
        )

        specialties = (
            db.query(Specialty)
            .filter(Specialty.code.like(f"{prefix}_%"))
            .all()
        )

        groups = (
            db.query(Group)
            .filter(Group.name.like(f"{prefix}-%"))
            .all()
        )

        students = (
            db.query(Student)
            .filter(Student.full_name.like(f"{prefix}%"))
            .all()
        )

        subjects = (
            db.query(Subject)
            .filter(Subject.code.like(f"{prefix}_%"))
            .all()
        )

        teachers = (
            db.query(Teacher)
            .filter(Teacher.full_name.like(f"{prefix}%"))
            .all()
        )

        classrooms = (
            db.query(Classroom)
            .filter(Classroom.name.like(f"{prefix}-%"))
            .all()
        )

        print(f"Учебных периодов : {len(academic_periods)}")
        print(f"Специальностей   : {len(specialties)}")
        print(f"Групп             : {len(groups)}")
        print(f"Студентов         : {len(students)}")
        print(f"Предметов         : {len(subjects)}")
        print(f"Преподавателей    : {len(teachers)}")
        print(f"Аудиторий         : {len(classrooms)}")

        # ---------------------------------------------------------
        # 2. Группы
        # ---------------------------------------------------------

        print()
        print("2. ГРУППЫ")
        print("-" * 80)

        for group in sorted(groups, key=lambda x: x.name):
            print(
                f"{group.name:25} | "
                f"курс={group.course} | "
                f"студентов={group.student_count} | "
                f"язык={group.language}"
            )

        # ---------------------------------------------------------
        # 3. Лекционные потоки
        # ---------------------------------------------------------

        print()
        print("3. ЛЕКЦИОННЫЕ ПОТОКИ")
        print("-" * 80)

        streams = (
            db.query(LectureStream)
            .filter(
                LectureStream.name.like(f"{prefix}%")
                | LectureStream.name.like("%TEST%")
            )
            .all()
        )

        if not streams:
            print("Лекционные потоки не найдены.")
        else:
            for stream in streams:
                group_count = len(stream.groups)
                student_count = len(stream.students)

                print(
                    f"{stream.name:45} | "
                    f"групп={group_count} | "
                    f"студентов={student_count} | "
                    f"active={stream.is_active}"
                )

        # ---------------------------------------------------------
        # 4. Подгруппы
        # ---------------------------------------------------------

        print()
        print("4. ПОДГРУППЫ")
        print("-" * 80)

        subgroup_sets = (
            db.query(SubgroupSet)
            .filter(SubgroupSet.lecture_stream_id.in_(
                [stream.id for stream in streams]
            ))
            .all()
        )

        subgroups = (
            db.query(Subgroup)
            .filter(Subgroup.subgroup_set_id.in_(
                [item.id for item in subgroup_sets]
            ))
            .all()
        )

        print(f"Наборов подгрупп: {len(subgroup_sets)}")
        print(f"Всего подгрупп   : {len(subgroups)}")

        for subgroup_set in subgroup_sets:
            print()
            print(
                f"Набор #{subgroup_set.id} | "
                f"версия={subgroup_set.version} | "
                f"статус={subgroup_set.status}"
            )

            set_subgroups = [
                subgroup
                for subgroup in subgroups
                if subgroup.subgroup_set_id == subgroup_set.id
            ]

            for subgroup in sorted(
                set_subgroups,
                key=lambda x: x.subgroup_number
            ):
                membership_count = (
                    db.query(func.count(SubgroupStudent.id))
                    .filter(
                        SubgroupStudent.subgroup_id == subgroup.id
                    )
                    .scalar()
                )

                print(
                    f"  {subgroup.name:45} | "
                    f"student_count={subgroup.student_count} | "
                    f"membership_rows={membership_count}"
                )

        # ---------------------------------------------------------
        # 5. Преподавательская нагрузка
        # ---------------------------------------------------------

        print()
        print("5. ПРЕПОДАВАТЕЛИ И НАГРУЗКА")
        print("-" * 80)

        teacher_loads = (
            db.query(TeacherLoad)
            .filter(
                TeacherLoad.teacher_id.in_(
                    [teacher.id for teacher in teachers]
                )
            )
            .all()
        )

        print(f"Всего нагрузок: {len(teacher_loads)}")

        total_lecture = 0
        total_practice = 0
        total_lab = 0

        for load in teacher_loads:
            teacher = load.teacher

            lecture = load.lecture_hours or 0
            practice = load.practice_hours or 0
            lab = load.lab_hours or 0

            total_lecture += lecture
            total_practice += practice
            total_lab += lab

            print(
                f"{teacher.full_name:35} | "
                f"lecture={lecture:3} | "
                f"practice={practice:3} | "
                f"lab={lab:3}"
            )

        print()
        print(
            f"ИТОГО часов: "
            f"лекции={total_lecture}, "
            f"практика={total_practice}, "
            f"лабы={total_lab}, "
            f"всего={total_lecture + total_practice + total_lab}"
        )

        # ---------------------------------------------------------
        # 6. Назначения преподавателей
        # ---------------------------------------------------------

        print()
        print("6. НАЗНАЧЕНИЯ ПРЕПОДАВАТЕЛЕЙ")
        print("-" * 80)

        assignments = (
            db.query(TeacherAssignment)
            .filter(
                TeacherAssignment.teacher_load_id.in_(
                    [load.id for load in teacher_loads]
                )
            )
            .all()
        )

        print(f"Назначений: {len(assignments)}")

        assignment_by_type = {}

        for assignment in assignments:
            target_type = assignment.target_type
            assignment_by_type[target_type] = (
                assignment_by_type.get(target_type, 0) + 1
            )

        for target_type, count in sorted(
            assignment_by_type.items()
        ):
            print(f"{target_type:15} : {count}")

        # ---------------------------------------------------------
        # 7. Занятия
        # ---------------------------------------------------------

        print()
        print("7. ЗАНЯТИЯ")
        print("-" * 80)

        assignment_ids = [
            assignment.id
            for assignment in assignments
        ]

        lessons = []

        if assignment_ids:
            lessons = (
                db.query(Lesson)
                .join(
                    Lesson.targets
                )
                .filter(
                    Lesson.targets.any(
                        TeacherAssignment.id.in_(assignment_ids)
                    )
                )
                .distinct()
                .all()
            )

        print(f"Занятий: {len(lessons)}")

        lesson_types = {}

        for lesson in lessons:
            lesson_types[lesson.lesson_type] = (
                lesson_types.get(lesson.lesson_type, 0) + 1
            )

        for lesson_type, count in sorted(
            lesson_types.items()
        ):
            print(f"{lesson_type:15} : {count}")

        # ---------------------------------------------------------
        # 8. Аудитории
        # ---------------------------------------------------------

        print()
        print("8. АУДИТОРИИ")
        print("-" * 80)

        for classroom in sorted(
            classrooms,
            key=lambda x: x.name
        ):
            print(
                f"{classroom.name:20} | "
                f"capacity={classroom.capacity:3} | "
                f"type={classroom.room_type:15} | "
                f"equipment={classroom.equipment or '-'}"
            )

        # ---------------------------------------------------------
        # 9. Контрольные проверки
        # ---------------------------------------------------------

        print()
        print("9. КОНТРОЛЬНЫЕ ПРОВЕРКИ")
        print("-" * 80)

        group_student_sum = sum(
            group.student_count
            for group in groups
        )

        print(
            f"Сумма студентов по группам: "
            f"{group_student_sum}"
        )

        print(
            f"Фактическое количество студентов: "
            f"{len(students)}"
        )

        if group_student_sum == len(students):
            print("✓ Студенты и группы согласованы")
        else:
            print("⚠ Несоответствие студентов и групп")

        active_sets = [
            item
            for item in subgroup_sets
            if item.status == "active"
        ]

        print(
            f"Активных наборов подгрупп: "
            f"{len(active_sets)}"
        )

        for subgroup_set in active_sets:
            set_subgroups = [
                subgroup
                for subgroup in subgroups
                if subgroup.subgroup_set_id == subgroup_set.id
            ]

            declared_students = sum(
                subgroup.student_count
                for subgroup in set_subgroups
            )

            membership_rows = (
                db.query(func.count(SubgroupStudent.id))
                .filter(
                    SubgroupStudent.subgroup_id.in_(
                        [s.id for s in set_subgroups]
                    )
                )
                .scalar()
            )

            print(
                f"  Набор #{subgroup_set.id}: "
                f"студентов={declared_students}, "
                f"membership_rows={membership_rows}"
            )

        print()
        print("=" * 80)
        print("ПРОВЕРКА ЗАВЕРШЕНА")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()