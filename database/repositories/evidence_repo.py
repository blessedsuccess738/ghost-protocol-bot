"""database/repositories/evidence_repo.py — Evidence persistence (Repository pattern)."""
import logging
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from models import Evidence

logger = logging.getLogger(__name__)


class EvidenceRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _session(self) -> Session:
        from database.connection import get_session
        return get_session()

    def add(self, case_id: int, evidence_type: str, reference: str, file_id: str | None = None,
            file_hash: str | None = None, file_size: int | None = None,
            file_type: str | None = None, description: str | None = None) -> Evidence:
        with self._session() as s:
            ev = Evidence(case_id=case_id, evidence_type=evidence_type, reference=reference,
                          file_id=file_id, file_hash=file_hash, file_size=file_size,
                          file_type=file_type, description=description)
            s.add(ev)
            s.commit()
            s.refresh(ev)
            return ev

    def add_many(self, items: list[dict]) -> list[Evidence]:
        created = []
        with self._session() as s:
            for i in range(0, len(items), 100):
                batch = items[i:i + 100]
                objs = [Evidence(**item) for item in batch]
                s.add_all(objs)
                s.flush()
                created.extend(objs)
            s.commit()
        return created

    def list_for_case(self, case_id: int) -> list[Evidence]:
        with self._session() as s:
            return list(s.scalars(select(Evidence).where(Evidence.case_id == case_id)))

    def count_for_case(self, case_id: int) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Evidence).where(Evidence.case_id == case_id)) or 0)

    def count_all(self) -> int:
        with self._session() as s:
            return int(s.scalar(select(func.count()).select_from(Evidence)) or 0)

    def get_by_id(self, evidence_id: int) -> Optional[Evidence]:
        with self._session() as s:
            return s.get(Evidence, evidence_id)

    def delete(self, evidence_id: int) -> bool:
        with self._session() as s:
            ev = s.get(Evidence, evidence_id)
            if ev is None:
                return False
            s.delete(ev)
            s.commit()
            return True
