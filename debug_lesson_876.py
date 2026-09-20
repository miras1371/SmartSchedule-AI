from backend.app.core.database import SessionLocal
from backend.app.scheduler.data_loader import load_scheduling_data
from backend.app.scheduler.scheduler import ScheduleGenerator
from ortools.sat.python import cp_model


ACADEMIC_PERIOD_ID = 10
LESSON_ID = 876


def main():
    db = SessionLocal()

    try:
        generator = ScheduleGenerator(
            db=db,
            academic_period_id=ACADEMIC_PERIOD_ID,
        )

        # Загружаем данные так же, как это делает generate()
        generator.data = load_scheduling_data(
            db=db,
            academic_period_id=ACADEMIC_PERIOD_ID,
        )

        generator._prepare_indexes()
        generator._validate_input_data()
        generator._create_variables()

        generator._add_each_lesson_exactly_one_slot()
        generator._add_each_target_exactly_one_classroom()
        generator._add_teacher_conflicts()
        generator._add_group_and_subgroup_conflicts()
        generator._add_classroom_conflicts()

        solver = cp_model.CpSolver()

        status = solver.Solve(
            generator.model
        )

        generator.solver = solver

        print("=" * 80)
        print("STATUS:", solver.StatusName(status))
        print("=" * 80)

        lesson = next(
            lesson
            for lesson in generator.data.lessons
            if lesson.lesson_id == LESSON_ID
        )

        print()
        print(f"Lesson #{lesson.lesson_id}")
        print(f"Тип: {lesson.lesson_type}")
        print(f"Предмет ID: {lesson.subject_id}")
        print(f"Количество targets: {len(lesson.targets)}")

        print()
        print("-" * 80)
        print("TARGETS")
        print("-" * 80)

        for target in lesson.targets:
            print(
                f"target #{target.target_id} | "
                f"type={target.target_type} | "
                f"students={target.student_count} | "
                f"teacher={target.teacher_id}"
            )

        print()
        print("-" * 80)
        print("ВЫБРАННЫЙ СЛОТ")
        print("-" * 80)

        selected_slot_id = None

        for slot in generator.data.time_slots:

            variable = generator.lesson_slot_bool[
                (
                    LESSON_ID,
                    slot.time_slot_id,
                )
            ]

            value = solver.Value(variable)

            if value == 1:
                selected_slot_id = slot.time_slot_id

                print(
                    f"slot #{slot.time_slot_id} "
                    f"day={slot.day_of_week} "
                    f"lesson={slot.lesson_number} "
                    f"-> 1"
                )

        print()
        print(
            f"SELECTED SLOT: {selected_slot_id}"
        )

        # ------------------------------------------------------------
        # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА SLOT #9
        # ------------------------------------------------------------

        print()
        print("-" * 80)
        print("ПРОВЕРКА SLOT #9")
        print("-" * 80)

        slot_9_variable = generator.lesson_slot_bool.get(
            (
                LESSON_ID,
                9,
            )
        )

        if slot_9_variable is None:
            print(
                "Переменная lesson_slot_bool[(876, 9)] НЕ НАЙДЕНА"
            )
        else:
            print(
                "lesson_slot_bool[(876, 9)] =",
                solver.Value(slot_9_variable),
            )

        print()
        print("-" * 80)
        print("VALID CLASSROOMS ДЛЯ КАЖДОГО TARGET")
        print("-" * 80)

        for target in lesson.targets:

            valid_classrooms = (
                generator._get_valid_classrooms(
                    lesson=lesson,
                    target=target,
                )
            )

            print()
            print(
                f"Target #{target.target_id}:"
            )

            print(
                f"  valid classrooms: "
                f"{valid_classrooms}"
            )

            if selected_slot_id is not None:

                for classroom_id in valid_classrooms:

                    key = (
                        LESSON_ID,
                        target.target_id,
                        selected_slot_id,
                        classroom_id,
                    )

                    variable = (
                        generator.lesson_target_classroom_bool.get(
                            key
                        )
                    )

                    if variable is None:

                        print(
                            f"  room {classroom_id}: "
                            f"VARIABLE MISSING"
                        )

                    else:

                        print(
                            f"  room {classroom_id}: "
                            f"value={solver.Value(variable)}"
                        )

        print()
        print("=" * 80)
        print("ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()