from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=255,
    )


class StudentsCreate(BaseModel):
    students: list[StudentCreate]


class StudentUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    group_id: int
    lecture_stream_ids: list[int] = Field(default_factory=list)