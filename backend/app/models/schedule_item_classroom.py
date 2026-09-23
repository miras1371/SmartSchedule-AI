from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class ScheduleItemClassroom(Base):
    """Version-specific classroom selected for one lesson target."""

    __tablename__ = "schedule_item_classrooms"

    __table_args__ = (
        UniqueConstraint(
            "schedule_item_id",
            "lesson_target_id",
            name="uq_schedule_item_lesson_target_classroom",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    schedule_item_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_target_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classroom_id: Mapped[int] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    schedule_item = relationship(
        "ScheduleItem",
        back_populates="classroom_assignments",
    )
    lesson_target = relationship(
        "LessonTarget",
        back_populates="schedule_classroom_assignments",
    )
    classroom = relationship(
        "Classroom",
        back_populates="schedule_assignments",
    )
