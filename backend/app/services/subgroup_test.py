from backend.app.core.database import SessionLocal
from backend.app.models.group import Group
from backend.app.models.student import Student
from backend.app.services.subgroup_service import (
    create_subgroups_for_group,
)


def main():
    db = SessionLocal()

    try:
        group = Group(
            name="ИС-41",
            course=4,
            language="Русский",
            student_count=25,
        )

        db.add(group)
        db.flush()

        names = [
            "Абдрахманов Марат",
            "Алиев Тимур",
            "Ахметов Данияр",
            "Беков Арман",
            "Власов Иван",
            "Галимов Рустам",
            "Давлетов Айдар",
            "Ермеков Нурлан",
            "Жумабаев Али",
            "Иванов Алексей",
            "Кадыров Руслан",
            "Ким Александр",
            "Ковалев Дмитрий",
            "Лебедев Максим",
            "Мамедов Эльдар",
            "Назаров Данияр",
            "Омаров Санжар",
            "Петров Иван",
            "Рахимов Тимур",
            "Сафин Артем",
            "Тлеубергенов Аян",
            "Умаров Азамат",
            "Федоров Михаил",
            "Хасанов Ринат",
            "Шарипов Дамир",
        ]

        for name in names:
            db.add(
                Student(
                    full_name=name,
                    group_id=group.id,
                )
            )

        db.commit()

        subgroups = create_subgroups_for_group(
            db,
            group,
        )

        for subgroup in subgroups:
            print(
                f"{subgroup.name}: "
                f"{subgroup.student_count} студентов"
            )

            for membership in subgroup.memberships:
                print(
                    f"  - {membership.student.full_name}"
                )

    finally:
        db.close()


if __name__ == "__main__":
    main()