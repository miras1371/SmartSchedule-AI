from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class LectureStreamGroup(Base):
    __tablename__ = "lecture_stream_groups"

    __table_args__ = (
        UniqueConstraint(
            "lecture_stream_id",
            "group_id",
            name="uq_lecture_stream_group",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    lecture_stream_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lecture_streams.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey(
            "groups.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    lecture_stream = relationship(
        "LectureStream",
        back_populates="groups",
    )

    group = relationship(
        "Group",
    )