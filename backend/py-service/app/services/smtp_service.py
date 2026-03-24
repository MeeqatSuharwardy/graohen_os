"""SMTP service for sending notification emails (link-only, link+passcode)."""

from typing import Optional

import logging
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import settings

logger = logging.getLogger(__name__)

_smtp_available: Optional[bool] = None


def _smtp_configured() -> bool:
    """Check if SMTP is configured for sending."""
    return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)


async def send_notification_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    from_name: str = "FxMail Secure",
) -> bool:
    """
    Send a plaintext notification email via SMTP.

    Returns True if sent, False if SMTP not configured or send failed.
    """
    if not _smtp_configured():
        logger.warning("SMTP not configured (SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD). Skipping notification.")
        return False

    try:
        import aiosmtplib

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = formataddr((from_name, settings.SMTP_FROM))
        msg["To"] = to_email

        # Port 465: implicit TLS. Port 587: STARTTLS (aiosmtplib upgrades by default)
        use_tls = settings.SMTP_PORT == 465 and settings.SMTP_USE_TLS

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=use_tls,
        )
        logger.info(f"Notification email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {to_email}: {e}", exc_info=True)
        return False


async def send_secure_message_notification(
    *,
    to_email: str,
    sender_email: str,
    secure_link: str,
    notification_type: str,  # "link_only" | "link_and_passcode"
) -> bool:
    """
    Send notification for a secure message.

    link_only: body contains only the link
    link_and_passcode: body contains link + note that sender will share passcode separately
    """
    subject = f"Secure message from {sender_email}"
    if notification_type == "link_only":
        body = f"""You have a secure message from {sender_email}.

Open it here: {secure_link}

This message is encrypted. Only you can access it via the link above."""
    else:
        body = f"""You have a secure message from {sender_email}.

Open it here: {secure_link}

This message is protected with a passcode. The sender will share the passcode with you separately (e.g., by phone, Signal, or in person)."""
    return await send_notification_email(
        to_email=to_email,
        subject=subject,
        body=body,
        from_name="FxMail Secure",
    )
