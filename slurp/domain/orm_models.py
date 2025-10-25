from uuid import uuid4

from sqlalchemy import JSON
from sqlalchemy import Column
from sqlmodel import Field
from sqlmodel import SQLModel

from slurp.domain.models import Generation
from slurp.domain.models import TaskResult


class TaskResultORM(SQLModel, table=True):
    __tablename__ = "task_results"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    status_code: int = Field(nullable=False)
    headers: dict[str, str] = Field(sa_column=Column(JSON, nullable=False))
    content: str = Field(nullable=False)
    hash: str = Field(nullable=False, index=True)
    url: str = Field(nullable=False, index=True)
    title: str = Field(nullable=False, index=True)

    @staticmethod
    def from_result(result: TaskResult) -> "TaskResultORM":
        """
        Convert a TaskResult to a TaskResultORM instance.
        """
        return TaskResultORM(
            status_code=result.status_code or 0,
            headers=dict(result.headers) or {},
            content=result.content,
            hash=result.hash,
            url=result.url,
            title=result.title or "",
        )


class GenerationORM(SQLModel, table=True):
    __tablename__ = "generations"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    question_answers: dict[str, str] = Field(sa_column=Column(JSON, nullable=False))
    references: dict[str, TaskResult] = Field(sa_column=Column(JSON, nullable=False))
    language: str = Field(nullable=False, default="de", index=True)

    @staticmethod
    def from_generation(generation: Generation) -> "GenerationORM":
        """
        Convert a Generation to a GenerationORM instance.
        """
        return GenerationORM(
            question_answers={qa.question: qa.answer for qa in generation.question_answers},
            references=[
                {
                    "status_code": ref.status_code or 0,
                    "headers": dict(ref.headers) or {},
                    "content": ref.content,
                    "hash": ref.hash,
                    "url": ref.url,
                    "title": ref.title or "",
                }
                for ref in generation.references
            ],
            language=generation.language,
        )
