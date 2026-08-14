"""database/repositories/force_group_repo.py — Force-join group configuration (Repository pattern)."""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from models import ForceGroupSetting

logger = logging.getLogger(__name__)


class ForceGroupRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def get(self) -> Optional[ForceGroupSetting]:
        with self._session() as s:
            return s.scalar(select(ForceGroupSetting).order_by(ForceGroupSetting.id.desc()).limit(1))

    def get_or_create(self) -> ForceGroupSetting:
        with self._session() as s:
            row = s.scalar(select(ForceGroupSetting).order_by(ForceGroupSetting.id.desc()).limit(1))
            if row is None:
                row = ForceGroupSetting(enabled=0)
                s.add(row)
                s.commit()
                s.refresh(row)
            return row

    def configure(self, chat_id: int | None = None, chat_username: str | None = None,
                  chat_title: str | None = None, enabled: bool = False,
                  updated_by: int | None = None) -> ForceGroupSetting:
        with self._session() as s:
            row = s.scalar(select(ForceGroupSetting).order_by(ForceGroupSetting.id.desc()).limit(1))
            if row is None:
                row = ForceGroupSetting()
                s.add(row)
            if chat_id is not None:
                row.chat_id = chat_id
            if chat_username is not None:
                row.chat_username = chat_username
            if chat_title is not None:
                row.chat_title = chat_title
            row.enabled = 1 if enabled else 0
            if updated_by is not None:
                row.updated_by = updated_by
            s.commit()
            s.refresh(row)
            logger.info("ForceGroup configured: %s enabled=%s", chat_username or chat_id, enabled)
            return row

    def set_enabled(self, enabled: bool, updated_by: int | None = None) -> Optional[ForceGroupSetting]:
        row = self.get_or_create()
        return self.configure(chat_id=row.chat_id, chat_username=row.chat_username,
                              chat_title=row.chat_title, enabled=enabled, updated_by=updated_by)

    def remove(self) -> None:
        with self._session() as s:
            row = s.scalar(select(ForceGroupSetting).order_by(ForceGroupSetting.id.desc()).limit(1))
            if row is not None:
                s.delete(row)
                s.commit()
                logger.info("ForceGroup requirement removed")

    def is_enabled(self) -> bool:
        row = self.get()
        return bool(row and row.enabled)
