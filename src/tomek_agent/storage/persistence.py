import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.memory import InMemoryStore


@asynccontextmanager
async def create_checkpointer(data_dir: str) -> AsyncIterator[AsyncSqliteSaver]:
    """SQLite-backed checkpointer for per-thread conversation state."""
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "checkpoints.db")
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        yield checkpointer


def create_store() -> InMemoryStore:
    """In-memory store for cross-session agent memory."""
    return InMemoryStore()
