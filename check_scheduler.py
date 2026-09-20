import argparse

from ortools.sat.python import cp_model

from backend.app.core.database import SessionLocal
from backend.app.scheduler.data_loader import load_scheduling_data
from backend.app.scheduler.scheduler import ScheduleGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Проверка выполнимости расписания.",
    )
    parser.add_argument(
        "--academic-period-id",
        type=int,
        required=True,
        help="ID академического периода в базе данных.",
    )
    return parser.parse_args()


def create_generator(academic_period_id: int):
    db = SessionLocal()

    generator = ScheduleGenerator(
        db=db,
        academic_period_id=academic_period_id,
    )

    generator.data = load_scheduling_data(
        db,
        academic_period_id=academic_period_id,
    )

    generator._prepare_indexes()
    generator._validate_input_data()
    generator._create_variables()

    return db, generator


def add_classroom_conflicts_for_room_type(
    generator,
    room_type: str,
) -> None:
    assert generator.data is not None

    for slot in generator.data.time_slots:
        slot_id = slot.time_slot_id

        for classroom in generator.data.classrooms:
            if classroom.room_type != room_type:
                continue

            classroom_id = classroom.classroom_id

            variables = []

            for lesson in generator.data.lessons:

                # ЛЕКЦИЯ
                if lesson.lesson_type == "lecture":

                    if not lesson.targets:
                        continue

                    first_target = lesson.targets[0]

                    key = (
                        lesson.lesson_id,
                        first_target.target_id,
                        slot_id,
                        classroom_id,
                    )

                    variable = (
                        generator.lesson_target_classroom_bool.get(key)
                    )

                    if variable is not None:
                        variables.append(variable)

                # ПРАКТИКА / ЛАБОРАТОРНАЯ
                else:

                    for target in lesson.targets:

                        key = (
                            lesson.lesson_id,
                            target.target_id,
                            slot_id,
                            classroom_id,
                        )

                        variable = (
                            generator.lesson_target_classroom_bool.get(key)
                        )

                        if variable is not None:
                            variables.append(variable)

            if variables:
                generator.model.Add(sum(variables) <= 1)


def solve(generator):
    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 600
    solver.parameters.num_search_workers = 8
    solver.parameters.stop_after_first_solution = True

    status = solver.Solve(generator.model)

    print("STATUS =", solver.StatusName(status))

    return status


def main() -> None:
    args = parse_args()
    db, generator = create_generator(args.academic_period_id)

    try:
        # Базовые ограничения
        generator._add_each_lesson_exactly_one_slot()
        generator._add_each_target_exactly_one_classroom()
        generator._add_teacher_conflicts()
        generator._add_group_and_subgroup_conflicts()

        # Проверяем конфликты компьютерных лабораторий.
        add_classroom_conflicts_for_room_type(
            generator,
            "computer_lab",
        )

        solve(generator)
    finally:
        db.close()


if __name__ == "__main__":
    main()