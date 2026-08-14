"""
tests/test_attack_tools.py — Unit tests for the Verify Target tool suite.

Covers:
- Target extraction (username / t.me link / message link / invalid)
- Protected-target rejection
- AttackLog repository CRUD + pagination
- TargetVerifyService moderation case creation
- No DDOS / no bug-exploit code paths exist
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "test_attack.db")

import config  # noqa: E402
from models import Base  # noqa: E402
from database.connection import get_engine  # noqa: E402
from database.repositories.attack_log_repo import AttackLogRepository  # noqa: E402
from services.target_verify_service import (  # noqa: E402
    TargetVerifyService,
    extract_target,
    is_protected,
    TOOL_VERIFY,
    TOOL_BAN_REQUEST,
)


def test_extract_target_username():
    parsed = extract_target("@scam_channel")
    assert parsed is not None
    assert parsed["username"] == "scam_channel"
    assert parsed["link"] == "https://t.me/scam_channel"


def test_extract_target_tme_link():
    parsed = extract_target("https://t.me/scam_channel")
    assert parsed is not None
    assert parsed["username"] == "scam_channel"


def test_extract_target_message_link():
    parsed = extract_target("https://t.me/scam_channel/12345")
    assert parsed is not None
    assert parsed["username"] == "scam_channel"
    assert parsed["message_id"] == 12345


def test_extract_target_invalid():
    assert extract_target("not a telegram ref!") is None
    assert extract_target("") is None


def test_protected_targets():
    assert is_protected("telegram") is True
    assert is_protected("BotFather") is True
    assert is_protected("random_user") is False


def test_attack_log_repo_crud():
    engine = get_engine()
    Base.metadata.create_all(engine)
    repo = AttackLogRepository(engine)
    rec = repo.create(
        target="https://t.me/scam_channel",
        target_id=None,
        target_type="channel",
        tool_used=TOOL_VERIFY,
        status="SUCCESS",
        result="public page reachable",
        admin_id=1,
        admin_telegram_id=7590603733,
    )
    assert rec.id is not None
    assert rec.tool_used == TOOL_VERIFY

    rows, total = repo.history_for_admin(1, page=1, per_page=10)
    assert total >= 1
    assert rows[0].target == "https://t.me/scam_channel"

    assert repo.count_total() >= 1
    assert repo.count_by_tool(TOOL_VERIFY) >= 1


def test_moderation_case_creation():
    engine = get_engine()
    Base.metadata.create_all(engine)
    # Create a real admin row so the FK (admin_id) resolves
    from models import Admin
    from sqlalchemy.orm import Session
    with Session(engine) as s:
        admin_row = Admin(telegram_id=7590603733, username="owner_test", role="OWNER")
        s.add(admin_row)
        s.commit()
        s.refresh(admin_row)
        admin_db_id = admin_row.id

    service = TargetVerifyService()
    admin = {"id": admin_db_id, "telegram_id": 7590603733, "user_id": None}
    parsed = extract_target("@scam_channel")
    out = service.create_moderation_case(
        admin, parsed, reason="Scam/Fraud",
        description="Verified via Verify Target tool.",
    )
    assert out["ok"] is True
    assert out["case"].case_id.startswith("GP-")
    assert out["case"].status == "PENDING"


def test_no_ddos_or_bug_code():
    """Guard: the tool suite must not ship DDOS or bug-exploit EXECUTABLES.

    Textual mentions of 'DDOS' / 'bug' are allowed ONLY as documentation of
    their absence (e.g. 'No DDOS tool exists'). This test checks for actual
    executable tooling: callback branches, command handlers, socket use.
    """
    import handlers.attack as attack_mod
    import services.target_verify_service as svc_mod

    src = "\n".join([
        open(attack_mod.__file__, encoding="utf-8").read(),
        open(svc_mod.__file__, encoding="utf-8").read(),
    ])
    low = src.lower()
    # No actual DDOS executable: no /ddos handler, no "attack:ddos" callback,
    # no flood loops, no raw sockets.
    assert "def ddos" not in low
    assert "attack:ddos" not in low
    assert "commandhandler(\"ddos\"" not in low
    assert "socket" not in low
    # No bug-exploit executable: no "attack:bug" callback branch.
    assert "attack:bug" not in low


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"✅ {fn.__name__}")
            passed += 1
        except Exception as exc:
            print(f"❌ {fn.__name__}: {exc}")
    print(f"\n{passed}/{len(fns)} tests passed")
    sys.exit(0 if passed == len(fns) else 1)
