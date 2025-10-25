import asyncio
from dataclasses import dataclass

from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from slurp.domain.config import SQLiteConfig
from slurp.domain.models import TaskResult, Generation, QA
from slurp.domain.orm_models import TaskResultORM, GenerationORM
from slurp.domain.ports import TaskResultMutatorProtocol


@dataclass
class SqlitePersistence(TaskResultMutatorProtocol):
    sqlite_config: SQLiteConfig

    def __post_init__(self):
        if not self.sqlite_config.database:
            raise ValueError(
                "SQLite database path must be provided in the configuration."
            )

        # async engine for runtime operations
        self.async_engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.sqlite_config.database}",
            connect_args={"timeout": self.sqlite_config.timeout},
            echo=False,
        )
        # sync engine for migrations
        sync_engine = create_engine(
            f"sqlite:///{self.sqlite_config.database}",
            connect_args={"timeout": self.sqlite_config.timeout},
            echo=False,
        )

        # run auto-migration (create tables)
        SQLModel.metadata.create_all(sync_engine, checkfirst=True)

        # session factory
        self.make_session = sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def __call__(self, response: TaskResult | Generation) -> TaskResult:
        async with self.make_session() as session:
            ent = TaskResultORM.from_result(response) if isinstance(response, TaskResult) else GenerationORM.from_generation(
                response)
            session.add(ent)
            await session.commit()
        return response


if __name__ == "__main__":
    import asyncio
    from slurp.domain.config import SQLiteConfig
    from slurp.domain.models import TaskResult

    # load config (uses SQLITE_DATABASE, SQLITE_TIMEOUT, SQLITE_CHECK_SAME_THREAD env vars)
    cfg = SQLiteConfig.from_env()
    persistence = SqlitePersistence(sqlite_config=cfg)

    # example TaskResult
    sample = TaskResult(
        status_code=200,
        headers={"X-Example": "true"},
        content="Hello, world!",
        hash="example-hash",
        url="http://example.com",
        title="Example Title",
    )

    generation_sample = Generation(
        question_answers=[QA("What is the capital of France?", "Paris", ["Paris is the capital of France."])],
        references=[TaskResult(
            status_code=200,
            headers={"X-Example": "true"},
            content="Hello, world!",
            hash="example-hash",
            url="http://example.com",
            title="Example Title",
        )],
    )

    # run persistence and print result
    print(asyncio.run(persistence(sample)))
    print(asyncio.run(persistence(generation_sample)))
