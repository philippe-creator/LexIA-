import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger
from core.config import settings

SMTP_HOST = getattr(settings, "SMTP_HOST", "")
SMTP_PORT = getattr(settings, "SMTP_PORT", 587)
SMTP_USER = getattr(settings, "SMTP_USER", "")
SMTP_PASSWORD = getattr(settings, "SMTP_PASSWORD", "")
SMTP_FROM = getattr(settings, "SMTP_FROM", SMTP_USER)
SMTP_USE_TLS = getattr(settings, "SMTP_USE_TLS", True)


def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP non configuré — email non envoyé.")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    if text:
        msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to, msg.as_string())
        logger.info(f"Email envoyé à {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Erreur envoi email à {to}: {e}")
        return False
