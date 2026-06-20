"""
email_sender.py — Send bulk emails via Resend (https://resend.com).
Requires RESEND_API_KEY set as an environment variable.
"""

import os
import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")

FROM_ADDRESS = os.environ.get("EMAIL_FROM", "TheFAB <onboarding@resend.dev>")


def send_newsletter(subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    """
    Send a plain-text email to every address in recipients.
    Returns (success: bool, message: str).
    """
    if not resend.api_key:
        return False, "RESEND_API_KEY is not configured"

    if not recipients:
        return False, "No recipients found"

    failed = 0
    for email in recipients:
        try:
            resend.Emails.send({
                "from": FROM_ADDRESS,
                "to": [email],
                "subject": subject,
                "text": body,
            })
        except Exception:
            failed += 1

    if failed == len(recipients):
        return False, "All sends failed — check your RESEND_API_KEY and EMAIL_FROM"
    if failed:
        return True, f"Sent to {len(recipients) - failed} subscriber(s); {failed} failed"
    return True, f"Sent to {len(recipients)} subscriber(s)"
