import argparse

from backend.app.core.database import SessionLocal
from backend.app.scheduler.scheduler import generate_schedule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Генерация расписания для академического периода.",
    )
    parser.add_argument(
        "--academic-period-id",
        type=int,
        required=True,
        help="ID академического периода в базе данных.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    db = SessionLocal()

    try:
        print("=" * 80)
        print("ГЕНЕРАЦИЯ РАСПИСАНИЯ")
        print("=" * 80)

        version = generate_schedule(
            db=db,
            academic_period_id=args.academic_period_id,
        )

        print()
        print("=" * 80)
        print("РАСПИСАНИЕ УСПЕШНО СОЗДАНО")
        print("=" * 80)

        print(f"Version ID: {version.id}")
        print(f"Название: {version.name}")
        print(f"Статус: {version.status}")

    finally:
        db.close()


if __name__ == "__main__":
    main()