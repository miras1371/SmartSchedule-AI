import argparse

from backend.app.core.database import SessionLocal
from backend.app.scheduler.data_loader import load_scheduling_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Проверка загруженных данных расписания.",
    )
    parser.add_argument(
        "--academic-period-id",
        type=int,
        required=True,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()

    try:
        data = load_scheduling_data(
            db,
            academic_period_id=args.academic_period_id,
        )

        print("=== ДАННЫЕ ДЛЯ ПЛАНИРОВЩИКА ===")
        print()

        print(f"Учебный период: {data.academic_period_id}")
        print(f"Занятий: {len(data.lessons)}")
        print(f"Временных слотов: {len(data.time_slots)}")
        print(f"Аудиторий: {len(data.classrooms)}")
        print()

        print("Первые 5 занятий:")
        for lesson in data.lessons[:5]:
            print(
                f"  Lesson #{lesson.lesson_id}: "
                f"{lesson.lesson_type}, "
                f"hours={lesson.hours}, "
                f"subject={lesson.subject_id}, "
                f"targets={len(lesson.targets)}"
            )

            for target in lesson.targets:
                print(
                    f"    - {target.target_type}: "
                    f"id={target.target_id}, "
                    f"students={target.student_count}, "
                    f"teacher_id={target.teacher_id}, "
                    f"assignment_id={target.teacher_assignment_id}"
                )

        print()

        print("Первые 3 временных слота:")
        for slot in data.time_slots[:3]:
            print(
                f"  Slot #{slot.time_slot_id}: "
                f"день={slot.day_of_week}, "
                f"пара={slot.lesson_number}, "
                f"{slot.start_time}–{slot.end_time}"
            )

        print()

        print("Аудитории:")
        for classroom in data.classrooms:
            print(
                f"  Classroom #{classroom.classroom_id}: "
                f"{classroom.name}, "
                f"capacity={classroom.capacity}, "
                f"type={classroom.room_type}"
            )

        print()
        print("✓ Данные успешно загружены.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
