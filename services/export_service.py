"""services/export_service.py — JSON / CSV / PDF export of system data."""
import csv
import io
import json
import logging
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

import config
from database.connection import get_engine
from database.repositories.admin_repo import AdminRepository
from database.repositories.audit_repo import AuditRepository
from database.repositories.case_repo import CaseRepository
from database.repositories.evidence_repo import EvidenceRepository
from database.repositories.settings_repo import SettingsRepository
from utils.helpers import ensure_dir

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self):
        self.export_dir = config.EXPORT_DIR
        ensure_dir(self.export_dir)

    def export_json(self, admin_id: int | None = None) -> str:
        admin_repo = AdminRepository(get_engine())
        case_repo = CaseRepository(get_engine())
        audit_repo = AuditRepository(get_engine())
        settings_repo = SettingsRepository(get_engine())
        cases, _ = case_repo.list_cases(admin_id=admin_id, page=1, per_page=100000)
        admins, _ = admin_repo.list_admins(page=1, per_page=100000)
        audits, _ = audit_repo.list_logs(admin_id=admin_id, page=1, per_page=100000)
        data = {"exported_at": datetime.utcnow().isoformat(), "version": config.BOT_VERSION,
                "admins": [self._admin_dict(a) for a in admins],
                "cases": [self._case_dict(c) for c in cases],
                "audit_logs": [{"id": a.id, "admin_id": a.admin_id, "action": a.action,
                                "details": a.details, "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                                "severity": a.severity} for a in audits],
                "settings": settings_repo.all()}
        path = os.path.join(self.export_dir, f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, default=str, indent=2, ensure_ascii=False)
        logger.info("JSON export written: %s", path)
        return path

    def export_csv(self, kind: str, admin_id: int | None = None) -> str:
        admin_repo = AdminRepository(get_engine())
        case_repo = CaseRepository(get_engine())
        audit_repo = AuditRepository(get_engine())
        path = os.path.join(self.export_dir, f"{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if kind == "cases":
            cases, _ = case_repo.list_cases(admin_id=admin_id, page=1, per_page=100000)
            rows = [[c.case_id, c.admin_id, c.target_link, c.reason, c.severity, c.status,
                     c.created_at.isoformat() if c.created_at else "", c.description or ""] for c in cases]
            header = ["case_id", "admin_id", "target_link", "reason", "severity", "status", "created_at", "description"]
        elif kind == "admins":
            admins, _ = admin_repo.list_admins(page=1, per_page=100000)
            rows = [[a.id, a.telegram_id, a.username or "", a.email or "", a.email_verified,
                     a.role, a.is_active, a.last_login.isoformat() if a.last_login else ""] for a in admins]
            header = ["id", "telegram_id", "username", "email", "email_verified", "role", "is_active", "last_login"]
        elif kind == "audit":
            audits, _ = audit_repo.list_logs(admin_id=admin_id, page=1, per_page=100000)
            rows = [[a.id, a.admin_id or "", a.action, a.severity,
                     a.timestamp.isoformat() if a.timestamp else ""] for a in audits]
            header = ["id", "admin_id", "action", "severity", "timestamp"]
        else:
            raise ValueError(f"Unknown CSV kind: {kind}")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        logger.info("CSV export written: %s", path)
        return path

    def export_pdf(self, case_ids: list[str] | None = None) -> str:
        case_repo = CaseRepository(get_engine())
        evidence_repo = EvidenceRepository(get_engine())
        path = os.path.join(self.export_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                                topMargin=18 * mm, bottomMargin=18 * mm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=18, spaceAfter=6)
        h2 = ParagraphStyle("H2X", parent=styles["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=4)
        body = ParagraphStyle("BodyX", parent=styles["BodyText"], fontSize=10, leading=14)
        story = [Paragraph("『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT — Case Summary", title_style),
                 Spacer(1, 6),
                 Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", body),
                 Spacer(1, 12)]
        cases = []
        if case_ids:
            for cid in case_ids:
                case = case_repo.get_by_case_id(cid)
                if case:
                    cases.append(case)
        else:
            cases, _ = case_repo.list_cases(page=1, per_page=100000)
        if not cases:
            story.append(Paragraph("No cases found.", body))
        else:
            for case in cases:
                story.append(Paragraph(f"{case.case_id}", h2))
                data = [["Target", case.target_link], ["Reason", case.reason],
                        ["Severity", case.severity], ["Status", case.status],
                        ["Created", case.created_at.strftime("%Y-%m-%d %H:%M") if case.created_at else "—"],
                        ["Description", (case.description or "—")[:400]]]
                table = Table(data, colWidths=[40 * mm, 125 * mm])
                table.setStyle(TableStyle([
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]))
                story.append(table)
                ev_count = evidence_repo.count_for_case(case.id)
                story.append(Paragraph(f"Evidence items: {ev_count}", body))
                story.append(Spacer(1, 10))
        doc.build(story)
        logger.info("PDF export written: %s", path)
        return path

    @staticmethod
    def _admin_dict(a) -> dict:
        return {"id": a.id, "telegram_id": a.telegram_id, "username": a.username, "email": a.email,
                "email_verified": a.email_verified, "role": a.role, "is_active": a.is_active,
                "last_login": a.last_login.isoformat() if a.last_login else None,
                "created_at": a.created_at.isoformat() if a.created_at else None}

    @staticmethod
    def _case_dict(c) -> dict:
        return {"case_id": c.case_id, "admin_id": c.admin_id, "target_link": c.target_link,
                "target_type": c.target_type, "target_name": c.target_name, "reason": c.reason,
                "description": c.description, "severity": c.severity, "status": c.status,
                "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
                "closed_at": c.closed_at.isoformat() if c.closed_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None}


export_service = ExportService()
