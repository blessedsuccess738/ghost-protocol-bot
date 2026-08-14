"""handlers/report.py — Compatibility shim (v2.0.0).
The REPORT workflow was rebranded to the BAN REQUEST workflow in v2.0.0.
This module re-exports the handlers from ban_request.py for any legacy import.
"""
from .ban_request import *  # noqa: F401,F403
from .ban_request import _new_ban_request, ban_request_command, target_input  # noqa: F401
