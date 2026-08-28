import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from loguru import logger

from core.config import settings

# Champs déclarés dans core/config.py (Settings) — lus ici en constantes de
# module pour rester simple à appeler depuis send_email().
BREVO_API_KEY = settings.BREVO_API_KEY
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASSWORD = settings.SMTP_PASSWORD
SMTP_FROM = settings.SMTP_FROM or SMTP_USER
SMTP_USE_TLS = settings.SMTP_USE_TLS

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _send_via_brevo(to: str, subject: str, html: str, text: str) -> bool:
    payload = {
        "sender": {"email": SMTP_FROM},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html,
    }
    if text:
        payload["textContent"] = text
    try:
        resp = requests.post(
            BREVO_API_URL,
            json=payload,
            headers={"api-key": BREVO_API_KEY, "content-type": "application/json"},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.info(f"Email envoyé à {to} via Brevo: {subject}")
            return True
        logger.error(f"Erreur envoi email (Brevo) à {to}: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Erreur envoi email (Brevo) à {to}: {e}")
        return False


def _send_via_smtp(to: str, subject: str, html: str, text: str) -> bool:
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
        logger.info(f"Email envoyé à {to} via SMTP: {subject}")
        return True
    except Exception as e:
        logger.error(f"Erreur envoi email (SMTP) à {to}: {e}")
        return False


def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    if BREVO_API_KEY and SMTP_FROM:
        return _send_via_brevo(to, subject, html, text)
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        return _send_via_smtp(to, subject, html, text)
    logger.warning("Aucun fournisseur d'email configuré (BREVO_API_KEY ou SMTP_HOST) — email non envoyé.")
    return False
