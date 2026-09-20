from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class TeacherAssignmentTarget(Base):
    __tablename__ = "teacher_assignment_targets"

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
            name="ck_assignment_target_target_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    teacher_assignment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "teacher_assignments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    teacher_assignment = relationship(
        "TeacherAssignment",
        back_populates="targets",
    )

    group = relationship(
        "Group",
    )

    lecture_part = relationship(
        "LecturePart",
    )

    subgroup = relationship(
        "Subgroup",
    )