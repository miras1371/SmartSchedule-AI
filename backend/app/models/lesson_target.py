from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class LessonTarget(Base):
    __tablename__ = "lesson_targets"

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
            OR
            (
                target_type = 'subgroup_bundle'
                AND group_id IS NULL
                AND subgroup_id IS NULL
                AND lecture_part_id IS NULL
                AND subgroup_bundle_id IS NOT NULL
            )
            """,
            name="ck_lesson_target_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lessons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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

    subgroup_bundle_id: Mapped[int | None] = mapped_column(
        ForeignKey("subgroup_bundles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    classroom_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "classrooms.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    lesson = relationship(
        "Lesson",
        back_populates="targets",
    )

    teacher_assignment = relationship(
        "TeacherAssignment",
        back_populates="lesson_targets",
    )

    group = relationship(
        "Group",
    )

    subgroup = relationship(
        "Subgroup",
    )

    lecture_part = relationship(
        "LecturePart",
    )

    subgroup_bundle = relationship(
        "SubgroupBundle",
    )

    classroom = relationship(
        "Classroom",
        back_populates="lesson_targets",
    )