from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class TimeSlot(Base):
    __tablename__ = "time_slots"

    __table_args__ = (
        UniqueConstraint(
            "day_of_week",
            "lesson_number",
            name="uq_time_slot_day_lesson_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    day_of_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    lesson_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    schedule_items = relationship(
    "ScheduleItem",
    back_populates="time_slot",
    )