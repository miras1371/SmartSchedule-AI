from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    lesson_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    lesson_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    targets = relationship(
        "LessonTarget",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )

    schedule_items = relationship(
    "ScheduleItem",
    back_populates="lesson",
    cascade="all, delete-orphan",
    )

    subgroup_bundles = relationship(
        "SubgroupBundle",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )