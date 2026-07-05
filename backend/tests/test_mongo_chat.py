"""Mongo chat history ordering tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.db import mongo


def test_get_chat_history_returns_recent_turns_in_chronological_order():
    docs = [
        {
            "_id": "3",
            "role": "assistant",
            "content": "third",
            "created_at": datetime(2026, 7, 5, 12, 0, tzinfo=timezone.utc),
        },
        {
            "_id": "2",
            "role": "user",
            "content": "second",
            "created_at": datetime(2026, 7, 5, 11, 0, tzinfo=timezone.utc),
        },
        {
            "_id": "1",
            "role": "assistant",
            "content": "first",
            "created_at": datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc),
        },
    ]

    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.limit.return_value = docs

    mock_coll = MagicMock()
    mock_coll.find.return_value = mock_cursor

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    with patch("app.db.mongo.get_db", return_value=mock_db):
        history = mongo.get_chat_history("app-123", limit=3)

    mock_cursor.sort.assert_called_once()
    assert history == [
        {"role": "assistant", "content": "first"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "third"},
    ]


def test_save_chat_turn_sets_created_at():
    mock_coll = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_coll

    with patch("app.db.mongo.get_db", return_value=mock_db):
        mongo.save_chat_turn("app-123", "user", "hello")

    inserted = mock_coll.insert_one.call_args[0][0]
    assert inserted["application_id"] == "app-123"
    assert inserted["role"] == "user"
    assert inserted["content"] == "hello"
    assert inserted["created_at"].tzinfo == timezone.utc
