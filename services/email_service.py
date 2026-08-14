"""services/email_service.py — SMTP email sending with simulated fallback."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.host = config.SMTP_HOST
        self.port = config.SMTP_PORT
        self.user = config.SMTP_USER
        self.password = config.SMTP_PASSWORD
        self.from_addr = config.EMAIL_FROM
        self.enabled = bool(self.user and self.password)

    def _send(self, to: str, subject: str, html: str) -> bool:
        if not self.enabled:
            logger.info("[simulated-email] to=%s subject=%s", to, subject)
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = to
            msg.attach(MIMEText(html, "html", "utf-8"))
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_addr, [to], msg.as_string())
            logger.info("Email sent to %s: %s", to, subject)
            return True
        except Exception as exc:
            logger.error("Email send failed: %s", exc)
            return False

    def send_verification(self, to: str, token: str, hours: int = 24) -> bool:
        subject = f"『𝑮𝑷』 𝑮𝑯𝑶𝑺𝑻 𝑷𝑹𝑶𝑻𝑶𝑪𝑶𝑳 BOT — Verify your email"
        html = (f"<h2>Email Verification</h2><p>Your verification token:</p>"
                f"<p style='font-size:20px;font-weight:bold'>{token}</p>"
                f"<p>Valid for {hours} hours.</p>")
        return self._send(to, subject, html)

    def send_case_created(self, to: str, case_id: str, target: str, reason: str) -> bool:
        subject = f"New BAN REQUEST {case_id}"
        html = f"<h3>New BAN REQUEST {case_id}</h3><p>Target: {target}</p><p>Reason: {reason}</p>"
        return self._send(to, subject, html)

    def send_broadcast(self, to: str, message: str) -> bool:
        subject = "📢 Broadcast"
        html = f"<p>{message}</p>"
        return self._send(to, subject, html)


email_service = EmailService()
