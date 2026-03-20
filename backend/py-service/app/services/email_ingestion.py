"""Email ingestion - receive emails from Postfix/SMTP (Gmail, Yahoo, etc.)."""

import email.utils
import logging
from email import policy
from email.parser import BytesParser
from app.config import settings
from app.services.email_service_postgres import EmailServicePostgres, get_email_service_mongodb

logger = logging.getLogger(__name__)

EMAIL_DOMAIN = settings.EMAIL_DOMAIN
MIN_TOKEN_LENGTH = 32  # Same as validation elsewhere


class EmailIngestionError(Exception):
    pass


def _extract_token_from_recipient(recipient: str) -> str | None:
    """
    Extract token from recipient like 'token@fxmail.ai' or 'token+tag@fxmail.ai'.
    Returns the local part (token) if domain matches, else None.
    """
    if not recipient or "@" not in recipient:
        return None
    local, domain = recipient.strip().lower().rsplit("@", 1)
    if domain != EMAIL_DOMAIN:
        return None
    # Strip +tag if present
    if "+" in local:
        local = local.split("+")[0]
    return local if len(local) >= 8 else None  # Basic sanity


def _parse_incoming_email(email_bytes: bytes) -> tuple[str, str, str, bytes]:
    """
    Parse raw email bytes. Returns (sender, subject, recipient_token, body_bytes).
    """
    msg = BytesParser(policy=policy.default).parsebytes(email_bytes)
    sender = ""
    if msg.get("From"):
        addrs = email.utils.getaddresses([msg["From"]])
        if addrs:
            sender = (addrs[0][1] or "").strip().lower()
    subject = (msg.get("Subject") or "").strip()
    recipient_token = ""
    for header in ("To", "Cc", "Delivered-To", "X-Original-To"):
        val = msg.get(header)
        if not val:
            continue
        for name, addr in email.utils.getaddresses([val]):
            token = _extract_token_from_recipient(addr)
            if token:
                recipient_token = token
                break
        if recipient_token:
            break
    if not recipient_token:
        raise EmailIngestionError("No valid recipient token found")
    body = b""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "text" and part.get_content_subtype() == "plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload
                    break
        if not body and msg.get_body(preferencelist=("plain",)):
            body = msg.get_body(preferencelist=("plain",)).get_payload(decode=True) or b""
    else:
        body = msg.get_payload(decode=True) or b""
    if not body:
        body = b"(No content)"
    full_body = f"Subject: {subject}\n\n{body.decode('utf-8', errors='replace')}"
    return sender, subject, recipient_token, full_body.encode("utf-8")


def get_email_ingestion_service() -> "EmailIngestionService | None":
    """Return ingestion service if available."""
    try:
        return EmailIngestionService()
    except Exception:
        return None


class EmailIngestionService:
    """Ingest inbound emails (from Gmail, Yahoo, etc.) and store encrypted."""

    async def ingest_email(
        self,
        *,
        email_bytes: bytes,
        recipient_address: str | None = None,
    ) -> dict:
        """
        Ingest incoming email. recipient_address can override (from Postfix X-Recipient/To).

        Returns: email_id, status, message, sender, recipient
        """
        try:
            if recipient_address:
                token = _extract_token_from_recipient(recipient_address)
                if not token:
                    raise EmailIngestionError(f"Invalid recipient: {recipient_address}")
            else:
                token = None
            sender, subject, parsed_token, body_bytes = _parse_incoming_email(email_bytes)
            if token is None:
                token = parsed_token
            if len(token) < 8:
                raise EmailIngestionError("Token too short")
            service = get_email_service_mongodb()
            result = await service.encrypt_and_store_inbound_email(
                email_body=body_bytes,
                sender_email=sender,
                recipient_token=token,
                subject=subject,
            )
            return {
                "email_id": result["access_token"],
                "status": "stored",
                "message": "Email encrypted and stored",
                "sender": sender,
                "recipient": f"{token}@{EMAIL_DOMAIN}",
            }
        except EmailIngestionError as e:
            raise
        except Exception as e:
            logger.error(f"Ingest failed: {e}", exc_info=True)
            raise EmailIngestionError(str(e)) from e
