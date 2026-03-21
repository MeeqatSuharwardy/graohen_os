"""PostgreSQL email service - stores encrypted emails in PostgreSQL."""

import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from app.core.encryption import (
    encrypt_bytes,
    decrypt_bytes,
    generate_key,
    EncryptionError,
)
from app.core.key_manager import (
    derive_key_from_passcode,
    generate_salt_for_identifier,
    get_key_manager,
)
from app.core.secure_derivation import derive_user_key_complex
from app.core import database
from app.config import settings
from app.models.email import StoredEmail
import logging

logger = logging.getLogger(__name__)

EMAIL_DOMAIN = settings.EMAIL_DOMAIN
EXTERNAL_HTTPS_BASE_URL = settings.EXTERNAL_HTTPS_BASE_URL
ACCESS_TOKEN_SIZE = 32


class EmailEncryptionError(Exception):
    pass


def _generate_public_access_token() -> str:
    """Generate a secure public access token for email access."""
    token_bytes = secrets.token_bytes(ACCESS_TOKEN_SIZE)
    return base64.urlsafe_b64encode(token_bytes).decode("utf-8").rstrip("=")


def _generate_secure_link(email_id: str, base_url: Optional[str] = None) -> str:
    """Generate secure HTTPS link for email access."""
    url = base_url or EXTERNAL_HTTPS_BASE_URL
    return f"{url.rstrip('/')}/email/{email_id}"


class EmailServicePostgres:
    """PostgreSQL email service - stores encrypted emails in PostgreSQL."""

    def __init__(self):
        self.key_manager = get_key_manager()

    async def encrypt_and_store_email(
        self,
        *,
        email_body: bytes,
        sender_email: str,
        recipient_emails: List[str],
        user_email: Optional[str] = None,
        passcode: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
        subject: Optional[str] = None,
        self_destruct: bool = False,
    ) -> Dict[str, Any]:
        """
        Encrypt email content and store in PostgreSQL.

        Returns:
            access_token, encryption_mode, email_address, secure_link, expires_at
        """
        if database.AsyncSessionLocal is None:
            raise EmailEncryptionError("Database not initialized")

        try:
            content_key = generate_key()
            encrypted_content = encrypt_bytes(email_body, content_key)

            if passcode:
                encryption_mode = "passcode_protected"
                if user_email:
                    salt = generate_salt_for_identifier(user_email)
                else:
                    salt = self.key_manager.generate_salt()

                base_key = derive_key_from_passcode(passcode, salt)
                ctx = salt + (user_email.encode() if user_email else b"passcode")
                passcode_key = derive_user_key_complex(base_key, ctx)
                encrypted_key_raw = encrypt_bytes(content_key, passcode_key)
                salt_base64 = base64.b64encode(salt).decode("utf-8")
                encrypted_content_key = {
                    "salt_base64": salt_base64,
                    "encrypted_key": encrypted_key_raw,
                }
            elif user_email:
                encryption_mode = "authenticated"
                # Encrypt content key for sender AND each fxmail.ai recipient (so both can read)
                per_user_keys: Dict[str, Dict[str, str]] = {}
                participants = [sender_email.lower().strip()]
                for r in recipient_emails:
                    r_lower = r.lower().strip()
                    if r_lower.endswith(f"@{EMAIL_DOMAIN}") and r_lower not in participants:
                        participants.append(r_lower)
                for participant in participants:
                    p_salt = generate_salt_for_identifier(participant)
                    p_base = derive_key_from_passcode(participant, p_salt)
                    p_key = derive_user_key_complex(
                        p_base, p_salt + participant.encode()
                    )
                    per_user_keys[participant] = encrypt_bytes(content_key, p_key)
                    p_key = b"\x00" * len(p_key)
                encrypted_content_key = {"per_user": per_user_keys}
            else:
                raise EmailEncryptionError(
                    "Either user_email or passcode must be provided"
                )

            access_token = _generate_public_access_token()
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

            async with database.AsyncSessionLocal() as session:
                stored = StoredEmail(
                    email_id=access_token,
                    sender_email=sender_email.lower().strip(),
                    recipient_emails=[e.lower().strip() for e in recipient_emails],
                    encrypted_content=encrypted_content,
                    encrypted_content_key=encrypted_content_key,
                    encryption_mode=encryption_mode,
                    has_passcode=passcode is not None,
                    is_draft=False,
                    subject=subject,
                    expires_at=expires_at,
                    self_destruct=self_destruct,
                )
                session.add(stored)
                await session.commit()

            email_address = f"{access_token}@{EMAIL_DOMAIN}"
            secure_link = _generate_secure_link(access_token)

            result = {
                "access_token": access_token,
                "encryption_mode": encryption_mode,
                "email_address": email_address,
                "secure_link": secure_link,
            }
            if expires_at:
                result["expires_at"] = expires_at.isoformat()

            logger.info(
                f"Email stored in PostgreSQL: mode={encryption_mode}, "
                f"token={access_token[:8]}..., expires={expires_at}"
            )
            return result

        except EncryptionError as e:
            logger.error(f"Email encryption failed: {e}", exc_info=True)
            raise EmailEncryptionError(f"Encryption failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Email storage failed: {e}", exc_info=True)
            raise EmailEncryptionError(f"Storage failed: {str(e)}") from e
        finally:
            if "content_key" in locals():
                content_key = b"\x00" * len(content_key)
            if "passcode_key" in locals():
                passcode_key = b"\x00" * len(passcode_key) if passcode_key else b""
            if "user_key" in locals():
                user_key = b"\x00" * len(user_key) if user_key else b""

    async def encrypt_and_store_inbound_email(
        self,
        *,
        email_body: bytes,
        sender_email: str,
        recipient_token: str,
        subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store inbound email (from Gmail, Yahoo, etc.) encrypted with token as passcode.
        email_id = recipient_token so link fxmail.ai/email/{token} works.
        """
        if database.AsyncSessionLocal is None:
            raise EmailEncryptionError("Database not initialized")
        recipient_token = recipient_token.strip().lower()
        recipient_addr = f"{recipient_token}@{EMAIL_DOMAIN}"
        try:
            content_key = generate_key()
            encrypted_content = encrypt_bytes(email_body, content_key)
            encryption_mode = "passcode_protected"
            salt = self.key_manager.generate_salt()
            base_key = derive_key_from_passcode(recipient_token, salt)
            ctx = salt + b"inbound"
            passcode_key = derive_user_key_complex(base_key, ctx)
            encrypted_key_raw = encrypt_bytes(content_key, passcode_key)
            salt_base64 = base64.b64encode(salt).decode("utf-8")
            encrypted_content_key = {
                "salt_base64": salt_base64,
                "encrypted_key": encrypted_key_raw,
                "context": "inbound",  # Use ctx=salt+b"inbound" for decrypt
            }
            access_token = recipient_token
            async with database.AsyncSessionLocal() as session:
                stored = StoredEmail(
                    email_id=access_token,
                    sender_email=(sender_email or "unknown@external").lower().strip(),
                    recipient_emails=[recipient_addr],
                    encrypted_content=encrypted_content,
                    encrypted_content_key=encrypted_content_key,
                    encryption_mode=encryption_mode,
                    has_passcode=True,
                    is_draft=False,
                    subject=subject,
                    expires_at=None,
                    self_destruct=False,
                )
                session.add(stored)
                await session.commit()
            return {
                "access_token": access_token,
                "encryption_mode": encryption_mode,
                "email_address": f"{access_token}@{EMAIL_DOMAIN}",
                "secure_link": _generate_secure_link(access_token),
            }
        except EncryptionError as e:
            raise EmailEncryptionError(f"Encryption failed: {str(e)}") from e
        finally:
            if "content_key" in locals():
                content_key = b"\x00" * len(content_key)
            if "passcode_key" in locals():
                passcode_key = b"\x00" * len(passcode_key) if passcode_key else b""

    async def _get_stored_email(self, email_id: str):
        """Fetch StoredEmail by email_id. Returns None if not found or expired."""
        if database.AsyncSessionLocal is None:
            return None
        async with database.AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = select(StoredEmail).where(StoredEmail.email_id == email_id)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return None
            if row.expires_at and row.expires_at < datetime.now(timezone.utc):
                return None
            return row

    async def decrypt_email_for_authenticated_user(
        self,
        *,
        access_token: str,
        user_email: str,
        return_metadata: bool = False,
    ):
        """
        Decrypt email for authenticated user (sender or fxmail.ai recipient).

        Returns:
            If return_metadata=True: (email_body_bytes, metadata_dict)
            Else: (email_body_bytes,) - caller may unpack as (body,) or (body, meta)
        """
        stored = await self._get_stored_email(access_token)
        if not stored:
            raise EmailEncryptionError("Email not found or expired")

        if stored.encryption_mode != "authenticated":
            raise EmailEncryptionError("Email requires passcode unlock")

        user_lower = user_email.lower().strip()
        recipients = [r.lower().strip() for r in (stored.recipient_emails or [])]
        if stored.sender_email != user_lower and user_lower not in recipients:
            raise EmailEncryptionError("Access denied: email belongs to different user")

        encrypted_content = stored.encrypted_content
        encrypted_content_key = stored.encrypted_content_key
        if not encrypted_content or not encrypted_content_key:
            raise EmailEncryptionError("Encrypted email data not found")

        # Resolve which encrypted key to use (per_user or legacy sender-only)
        key_payload = None
        if isinstance(encrypted_content_key, dict) and "per_user" in encrypted_content_key:
            per_user = encrypted_content_key.get("per_user") or {}
            key_payload = per_user.get(user_lower)
        if not key_payload and (stored.sender_email == user_lower):
            # Legacy format: flat {ciphertext, nonce, tag} for sender only
            if "ciphertext" in (encrypted_content_key or {}):
                key_payload = encrypted_content_key

        if not key_payload:
            raise EmailEncryptionError("Access denied: no decryption key for this user")

        try:
            user_salt = generate_salt_for_identifier(user_lower)
            base_key = derive_key_from_passcode(user_lower, user_salt)
            user_key = derive_user_key_complex(
                base_key, user_salt + user_lower.encode()
            )
            content_key = decrypt_bytes(key_payload, user_key)
            email_body = decrypt_bytes(encrypted_content, content_key)
            content_key = b"\x00" * len(content_key)
            user_key = b"\x00" * len(user_key)
        except EncryptionError as e:
            raise EmailEncryptionError(f"Failed to decrypt: {str(e)}") from e

        logger.info(
            f"Email decrypted for authenticated user: {user_email}, "
            f"token={access_token[:8]}..."
        )

        if return_metadata:
            metadata = {
                "sender_email": stored.sender_email,
                "recipient_emails": stored.recipient_emails or [],
                "subject": stored.subject,
                "encryption_mode": stored.encryption_mode,
                "has_passcode": stored.has_passcode,
                "self_destruct": stored.self_destruct,
                "expires_at": stored.expires_at.isoformat() if stored.expires_at else None,
            }
            return (email_body, metadata)
        return (email_body, {})

    async def decrypt_email_with_passcode(
        self,
        *,
        access_token: str,
        passcode: str,
    ) -> bytes:
        """Decrypt email using passcode."""
        stored = await self._get_stored_email(access_token)
        if not stored:
            raise EmailEncryptionError("Email not found or expired")

        if stored.encryption_mode != "passcode_protected":
            raise EmailEncryptionError("Email does not require passcode")

        if not stored.has_passcode:
            raise EmailEncryptionError("Email was not encrypted with passcode")

        encrypted_content = stored.encrypted_content
        encrypted_content_key = stored.encrypted_content_key
        if not encrypted_content or not encrypted_content_key:
            raise EmailEncryptionError("Encrypted email data not found")

        # Passcode mode: encrypted_content_key is {"salt_base64": "...", "encrypted_key": {...}}
        if isinstance(encrypted_content_key, dict) and "salt_base64" in encrypted_content_key:
            salt_base64 = encrypted_content_key.get("salt_base64")
            encrypted_key_raw = encrypted_content_key.get("encrypted_key")
            if not salt_base64 or not encrypted_key_raw:
                raise EmailEncryptionError("Invalid encrypted key structure")
            salt = base64.b64decode(salt_base64)
            is_inbound = encrypted_content_key.get("context") == "inbound"
            if is_inbound:
                ctx = salt + b"inbound"
            else:
                user_email = stored.sender_email
                ctx = salt + (user_email.encode() if user_email else b"passcode")
        else:
            raise EmailEncryptionError("Passcode salt not found")

        try:
            base_key = derive_key_from_passcode(passcode, salt)
            passcode_key = derive_user_key_complex(base_key, ctx)
            content_key = decrypt_bytes(encrypted_key_raw, passcode_key)
            email_body = decrypt_bytes(encrypted_content, content_key)
            content_key = b"\x00" * len(content_key)
            passcode_key = b"\x00" * len(passcode_key)
        except EncryptionError:
            raise EmailEncryptionError("Incorrect passcode") from None

        logger.info(f"Email decrypted with passcode: token={access_token[:8]}...")
        return email_body

    async def delete_email(self, email_id: str) -> bool:
        if database.AsyncSessionLocal is None:
            return False
        async with database.AsyncSessionLocal() as session:
            from sqlalchemy import select, delete
            stmt = delete(StoredEmail).where(StoredEmail.email_id == email_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def get_inbox_emails(
        self, user_email: str, limit: int = 50, offset: int = 0
    ) -> List[Dict]:
        if database.AsyncSessionLocal is None:
            return []
        async with database.AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = (
                select(StoredEmail)
                .where(
                    StoredEmail.recipient_emails.contains(
                        [user_email.lower()]
                    )
                )
                .order_by(StoredEmail.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "email_id": r.email_id,
                    "access_token": r.email_id,
                    "sender_email": r.sender_email,
                    "recipient_emails": r.recipient_emails or [],
                    "subject": r.subject,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "has_passcode": r.has_passcode,
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                    "is_draft": r.is_draft,
                    "status": "inbox",
                }
                for r in rows
            ]

    async def get_sent_emails(
        self, user_email: str, limit: int = 50, offset: int = 0
    ) -> List[Dict]:
        if database.AsyncSessionLocal is None:
            return []
        async with database.AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = (
                select(StoredEmail)
                .where(StoredEmail.sender_email == user_email.lower())
                .where(StoredEmail.is_draft == False)
                .order_by(StoredEmail.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "email_id": r.email_id,
                    "access_token": r.email_id,
                    "sender_email": r.sender_email,
                    "recipient_emails": r.recipient_emails or [],
                    "subject": r.subject,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "has_passcode": r.has_passcode,
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                    "is_draft": False,
                    "status": "sent",
                }
                for r in rows
            ]

    async def get_draft_emails(
        self, user_email: str, limit: int = 50, offset: int = 0
    ) -> List[Dict]:
        if database.AsyncSessionLocal is None:
            return []
        async with database.AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = (
                select(StoredEmail)
                .where(StoredEmail.sender_email == user_email.lower())
                .where(StoredEmail.is_draft == True)
                .order_by(StoredEmail.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "email_id": r.email_id,
                    "access_token": r.email_id,
                    "sender_email": r.sender_email,
                    "recipient_emails": r.recipient_emails or [],
                    "subject": r.subject,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "has_passcode": r.has_passcode,
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                    "is_draft": True,
                    "status": "draft",
                }
                for r in rows
            ]


def get_email_service_mongodb() -> EmailServicePostgres:
    return EmailServicePostgres()
