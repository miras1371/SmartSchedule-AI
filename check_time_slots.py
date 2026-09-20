from backend.app.core.database import SessionLocal
from backend.app.models.time_slot import TimeSlot


def main() -> None:
    db = SessionLocal()

    try:
        slots = (
            db.query(TimeSlot)
            .filter(TimeSlot.is_active.is_(True))
            .order_by(
                TimeSlot.day_of_week,
                TimeSlot.lesson_number,
            )
            .all()
        )

        print()
        print("=" * 70)
        print("ВРЕМЕННЫЕ СЛОТЫ")
        print("=" * 70)

        print(f"Всего активных слотов: {len(slots)}")
        print()

        day_names = {
            1: "Пн",
            2: "Вт",
            3: "Ср",
            4: "Чт",
            5: "Пт",
            6: "Сб",
        }

        current_day = None

        for slot in slots:
            if slot.day_of_week != current_day:
                current_day = slot.day_of_week
                print()
                print(day_names[current_day])

            print(
                f"  №{slot.lesson_number}: "
                f"{slot.start_time.strftime('%H:%M')}–"
                f"{slot.end_time.strftime('%H:%M')}"
            )

        print()

        if len(slots) == 42:
            print("✓ Создано ровно 42 временных слота.")
        else:
            print(
                f"⚠ Ожидалось 42 слота, "
                f"но найдено {len(slots)}."
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()