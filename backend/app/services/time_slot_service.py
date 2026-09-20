from datetime import time

from sqlalchemy.orm import Session

from backend.app.models.time_slot import TimeSlot


WEEK_DAYS = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
}


TIME_SLOTS = [
    (1, time(8, 0), time(8, 50)),
    (2, time(9, 0), time(9, 50)),
    (3, time(10, 0), time(10, 50)),
    (4, time(11, 0), time(11, 50)),
    (5, time(12, 0), time(12, 50)),
    (6, time(13, 0), time(13, 50)),
    (7, time(14, 0), time(14, 50)),
    (8, time(15, 0), time(15, 50)),
    (9, time(16, 0), time(16, 50)),
    (10, time(17, 0), time(17, 50)),
    (11, time(18, 0), time(18, 50)),
    (12, time(19, 0), time(19, 50)),
    (13, time(20, 0), time(20, 50)),
]


def create_default_time_slots(
    db: Session,
) -> list[TimeSlot]:
    existing_slots = {
        (slot.day_of_week, slot.lesson_number): slot
        for slot in db.query(TimeSlot).all()
    }

    for day_of_week in WEEK_DAYS:
        for lesson_number, start_time, end_time in TIME_SLOTS:
            if (day_of_week, lesson_number) in existing_slots:
                continue
            slot = TimeSlot(
                day_of_week=day_of_week,
                lesson_number=lesson_number,
                start_time=start_time,
                end_time=end_time,
                is_active=True,
            )

            db.add(slot)

    db.commit()

    return (
        db.query(TimeSlot)
        .filter(TimeSlot.is_active.is_(True))
        .order_by(TimeSlot.day_of_week, TimeSlot.lesson_number)
        .all()
    )