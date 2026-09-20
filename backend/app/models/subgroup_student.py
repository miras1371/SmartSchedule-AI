from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class SubgroupStudent(Base):
    __tablename__ = "subgroup_students"

    __table_args__ = (
        UniqueConstraint(
            "subgroup_id",
            "student_id",
            name="uq_subgroup_students_subgroup_student",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    subgroup_id: Mapped[int] = mapped_column(
        ForeignKey("subgroups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subgroup = relationship(
        "Subgroup",
        back_populates="students",
    )

    student = relationship("Student")