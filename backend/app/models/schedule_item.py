from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    schedule_version_id: Mapped[int] = mapped_column(
        ForeignKey(
            "schedule_versions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lessons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    time_slot_id: Mapped[int] = mapped_column(
        ForeignKey(
            "time_slots.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    schedule_version = relationship(
        "ScheduleVersion",
        back_populates="schedule_items",
    )

    lesson = relationship(
        "Lesson",
        back_populates="schedule_items",
    )

    time_slot = relationship(
        "TimeSlot",
        back_populates="schedule_items",
    )

    classroom_assignments = relationship(
        "ScheduleItemClassroom",
        back_populates="schedule_item",
        cascade="all, delete-orphan",
    )
