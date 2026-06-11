"""
email_sender.py — Send bulk emails to all subscribers via Gmail SMTP.
Requires SMTP_* variables set in .env.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_newsletter(subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    """
    Send a plain-text email to every address in recipients.
    Returns (success: bool, message: str).
    """
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    from_name = os.environ.get("EMAIL_FROM_NAME", "Artist")

    if not smtp_user or not smtp_password:
        return False, "SMTP credentials not configured in .env"

    if not recipients:
        return False, "No recipients found"

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)

            for email in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{from_name} <{smtp_user}>"
                msg["To"] = email
                msg.attach(MIMEText(body, "plain", "utf-8"))
                server.sendmail(smtp_user, email, msg.as_string())

        return True, f"Sent to {len(recipients)} subscriber(s)"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed — check your App Password in .env"
    except Exception as exc:
        return False, f"Send failed: {exc}"
