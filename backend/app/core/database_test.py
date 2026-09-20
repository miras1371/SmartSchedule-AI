from sqlalchemy import text

from backend.app.core.database import engine


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("DATABASE RESULT:", result.scalar())


if __name__ == "__main__":
    test_database_connection()