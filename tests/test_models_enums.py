"""Difficulty/Language enums behave as strings and serialize cleanly."""

import orjson

from slurp.adapters.kafka import KafkaQueueSubmitter
from slurp.domain.models import FormatterDifficulties
from slurp.domain.models import Languages
from slurp.domain.models import Task


def test_enums_compare_equal_to_strings():
    assert FormatterDifficulties.EASY == "EASY"
    assert Languages.DE == "de"


def test_enum_dict_lookup_by_string():
    table = {FormatterDifficulties.EASY: 1}
    assert table["EASY"] == 1


def test_task_with_enum_defaults_serializes_to_plain_json():
    task = Task(title="t", url="u", downloader="local", idempotency_key="k", metadata={})
    raw = KafkaQueueSubmitter.serialize_task(task)
    decoded = orjson.loads(raw)
    assert decoded["language"] == "de"
    assert decoded["difficulty"] == "MIXED"
