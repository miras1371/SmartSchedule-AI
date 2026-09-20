from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"

    __table_args__ = (
        CheckConstraint(
            """
            (
                target_type = 'full_group'
                AND group_id IS NOT NULL
                AND subgroup_id IS NULL
                AND lecture_part_id IS NULL
            )
            OR
            (
                target_type = 'subgroup'
                AND group_id IS NULL
                AND subgroup_id IS NOT NULL
                AND lecture_part_id IS NULL
            )
            OR
            (
                target_type = 'lecture_part'
                AND group_id IS NULL
                AND subgroup_id IS NULL
                AND lecture_part_id IS NOT NULL
            )
            """,
            name="ck_assignment_target",
        ),
        CheckConstraint(
            "lecture_hours >= 0",
            name="ck_assignment_lecture_hours_non_negative",
        ),
        CheckConstraint(
            "practice_hours >= 0",
            name="ck_assignment_practice_hours_non_negative",
        ),
        CheckConstraint(
            "lab_hours >= 0",
            name="ck_assignment_lab_hours_non_negative",
        ),
        CheckConstraint(
            "lecture_hours + practice_hours + lab_hours > 0",
            name="ck_assignment_hours_positive",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    teacher_load_id: Mapped[int] = mapped_column(
        ForeignKey(
            "teacher_loads.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="full_group",
        server_default="full_group",
    )

    group_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "groups.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    subgroup_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "subgroups.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    lecture_part_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "lecture_parts.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    lecture_hours: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    practice_hours: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    lab_hours: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    teacher_load = relationship(
        "TeacherLoad",
        back_populates="assignments",
    )

    group = relationship(
        "Group",
        back_populates="teacher_assignments",
    )

    subgroup = relationship(
        "Subgroup",
        back_populates="teacher_assignments",
    )

    lecture_part = relationship(
        "LecturePart",
    )

    targets = relationship(
        "TeacherAssignmentTarget",
        back_populates="teacher_assignment",
        cascade="all, delete-orphan",
    )

    lesson_targets = relationship(
        "LessonTarget",
        back_populates="teacher_assignment",
        cascade="all, delete-orphan",
    )