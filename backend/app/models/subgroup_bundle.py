from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class SubgroupBundle(Base):
    __tablename__ = "subgroup_bundles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_count: Mapped[int] = mapped_column(Integer, nullable=False)

    lesson = relationship("Lesson", back_populates="subgroup_bundles")
    members = relationship(
        "SubgroupBundleMember",
        back_populates="bundle",
        cascade="all, delete-orphan",
    )
