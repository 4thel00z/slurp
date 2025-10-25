from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from typing import TypedDict

from pydantic import BaseModel
from pydantic import Field


class FormatterDifficulties:
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    MIXED = "MIXED"
    BALANCED = "BALANCED"


class Languages:
    DE = "de"
    EN = "en"


@dataclass
class Task:
    title: str
    url: str
    downloader: str
    idempotency_key: str
    metadata: dict[str, Any]
    language: str = Languages.DE
    difficulty: str = FormatterDifficulties.MIXED
    temperature: float = 0.7


@dataclass
class TaskResult:
    title: str
    status_code: int
    headers: dict[str, str]
    content: str
    hash: str
    url: str
    language: str = Languages.DE
    difficulty: str = FormatterDifficulties.MIXED
    temperature: float = 0.7


@dataclass
class QA:
    question: str
    answer: str
    chunks: list[str]


class QuestionSchema(BaseModel):
    question: str = Field(..., description="The generated question text")


class AnswerSchema(BaseModel):
    answer: str = Field(..., description="The generated answer text")
    chunks: list[str] = Field(..., description="The relevant chunks from the document")


@dataclass
class Generation:
    question_answers: list[QA]
    references: Sequence[TaskResult]
    language: str = "de"


# Confluence-specific data models


class ProfilePicture(TypedDict):
    path: str
    width: int
    height: int
    isDefault: bool


class CreatedBy(TypedDict):
    type: str
    accountId: str
    accountType: str
    email: str
    publicName: str
    profilePicture: ProfilePicture
    displayName: str
    isExternalCollaborator: bool
    isGuest: bool
    locale: str
    accountStatus: str
    _expandable: dict[str, str]
    _links: dict[str, str]


class History(TypedDict):
    latest: bool
    createdBy: CreatedBy
    createdDate: str
    _expandable: dict[str, str]
    _links: dict[str, str]


class VersionBy(TypedDict):
    type: str
    accountId: str
    accountType: str
    email: str
    publicName: str
    timeZone: str
    profilePicture: ProfilePicture
    displayName: str
    isExternalCollaborator: bool
    isGuest: bool
    locale: str
    accountStatus: str
    _expandable: dict[str, str]
    _links: dict[str, str]


class Version(TypedDict):
    by: VersionBy
    when: str
    friendlyWhen: str
    message: str
    number: int
    minorEdit: bool
    ncsStepVersion: str
    ncsStepVersionSource: str
    confRev: str
    contentTypeModified: bool
    _expandable: dict[str, str]
    _links: dict[str, str]


class ConfluencePage(TypedDict):
    id: str
    type: str
    ari: str
    status: str
    title: str
    history: History
    version: Version
    macroRenderedOutput: dict[str, Any]
    extensions: dict[str, Any]
    _expandable: dict[str, str]
    _links: dict[str, str]
