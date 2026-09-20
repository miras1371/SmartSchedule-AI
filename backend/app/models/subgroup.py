from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Subgroup(Base):
    __tablename__ = "subgroups"

    __table_args__ = (
        UniqueConstraint(
            "subgroup_set_id",
            "group_id",
            "subgroup_number",
            name="uq_subgroup_set_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    subgroup_set_id: Mapped[int] = mapped_column(
        ForeignKey(
            "subgroup_sets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    subgroup_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    student_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    subgroup_set = relationship(
        "SubgroupSet",
        back_populates="subgroups",
    )

    group = relationship("Group")

    students = relationship(
        "SubgroupStudent",
        back_populates="subgroup",
        cascade="all, delete-orphan",
    )

    teacher_assignments = relationship(
        "TeacherAssignment",
        back_populates="subgroup",
        cascade="all, delete-orphan",
    )