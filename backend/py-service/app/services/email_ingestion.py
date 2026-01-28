"""Email Ingestion Service

Handles incoming emails from Postfix SMTP server.
Parses email content, extracts token from recipient address,
and stores encrypted email in MongoDB.
"""

import email
import email.utils
from email.parser import BytesParser
from typing import Optional, Dict, Any, List
import logging
import secrets
import re
from datetime import datetime

from app.core.mongodb import get_mongodb
from app.services.email_service_mongodb import get_email_service_mongodb
from app.config import settings

logger = logging.getLogger(__name__)


class EmailIngestionError(Exception):
    """Custom exception for email ingestion errors"""
    pass


class EmailIngestionService:
    """Service for ingesting incoming emails from Postfix"""
    
    def __init__(self):
        self.email_domain = settings.EMAIL_DOMAIN
        self.email_service = get_email_service_mongodb()
    
    def parse_email_from_bytes(self, email_bytes: bytes) -> Dict[str, Any]:
        """
        Parse email from raw bytes (from Postfix pipe).
        
        Args:
            email_bytes: Raw email bytes from Postfix
            
        Returns:
            Dictionary with parsed email fields
        """
        try:
            # Parse email
            msg = BytesParser().parsebytes(email_bytes)
            
            # Extract headers
            from_addr = msg.get("From", "")
            to_addrs = msg.get("To", "")
            subject = msg.get("Subject", "")
            date_str = msg.get("Date", "")
            
            # Parse From address
            from_email = self._extract_email_address(from_addr)
            
            # Parse To addresses (can be multiple)
            to_emails = self._extract_email_addresses(to_addrs)
            
            # Extract body
            body_text = self._extract_body(msg)
            
            # Parse date
            email_date = None
            if date_str:
                try:
                    email_date = email.utils.parsedate_to_datetime(date_str)
                except Exception:
                    email_date = datetime.utcnow()
            else:
                email_date = datetime.utcnow()
            
            return {
                "from_email": from_email,
                "to_emails": to_emails,
                "subject": subject,
                "body": body_text,
                "date": email_date,
                "raw_headers": dict(msg.items()),
            }
            
        except Exception as e:
            logger.error(f"Failed to parse email: {e}", exc_info=True)
            raise EmailIngestionError(f"Failed to parse email: {str(e)}") from e
    
    def _extract_email_address(self, address_string: str) -> Optional[str]:
        """Extract email address from header string"""
        if not address_string:
            return None
        
        # Try to parse with email.utils
        try:
            parsed = email.utils.parseaddr(address_string)
            if parsed[1]:
                return parsed[1].lower().strip()
        except Exception:
            pass
        
        # Fallback: regex extraction
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', address_string)
        if match:
            return match.group(0).lower().strip()
        
        return None
    
    def _extract_email_addresses(self, addresses_string: str) -> List[str]:
        """Extract multiple email addresses from header string"""
        if not addresses_string:
            return []
        
        emails = []
        
        # Split by comma and parse each
        for addr in addresses_string.split(","):
            email_addr = self._extract_email_address(addr.strip())
            if email_addr:
                emails.append(email_addr)
        
        return emails
    
    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract email body (prefer text/plain, fallback to text/html)"""
        body_text = ""
        body_html = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        body_text = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                elif content_type == "text/html":
                    try:
                        body_html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except Exception:
                        pass
        else:
            # Single part message
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    if content_type == "text/html":
                        body_html = payload.decode("utf-8", errors="ignore")
                    else:
                        body_text = payload.decode("utf-8", errors="ignore")
            except Exception:
                pass
        
        # Prefer plain text, fallback to HTML (strip tags)
        if body_text:
            return body_text.strip()
        elif body_html:
            # Simple HTML tag removal (basic)
            import re
            text = re.sub(r'<[^>]+>', '', body_html)
            return text.strip()
        
        return ""
    
    def extract_token_from_address(self, email_address: str) -> Optional[str]:
        """
        Extract token from email address (e.g., token@fxmail.ai -> token).
        
        Args:
            email_address: Full email address
            
        Returns:
            Token string or None if not a valid token address
        """
        if not email_address:
            return None
        
        email_address = email_address.lower().strip()
        
        # Check if it's our domain
        if not email_address.endswith(f"@{self.email_domain}"):
            return None
        
        # Extract local part (token)
        local_part = email_address.split("@")[0]
        
        # Validate token format (should be URL-safe base64-like)
        if len(local_part) >= 32:  # Minimum token length
            return local_part
        
        return None
    
    async def ingest_email(
        self,
        email_bytes: bytes,
        recipient_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingest incoming email from Postfix.
        
        Args:
            email_bytes: Raw email bytes
            recipient_address: Optional recipient address (from Postfix)
            
        Returns:
            Dictionary with ingestion result
        """
        try:
            # Parse email
            parsed = self.parse_email_from_bytes(email_bytes)
            
            # Extract token from recipient
            # Priority: recipient_address parameter > first To address
            recipient_email = recipient_address or (parsed["to_emails"][0] if parsed["to_emails"] else None)
            
            if not recipient_email:
                raise EmailIngestionError("No recipient address found")
            
            token = self.extract_token_from_address(recipient_email)
            
            if not token:
                # Not a token-based address, reject
                raise EmailIngestionError(f"Invalid recipient address format: {recipient_email}")
            
            # Validate token entropy
            if len(token) < 32:
                raise EmailIngestionError(f"Token too short: {len(token)} < 32")
            
            # Get sender email
            sender_email = parsed["from_email"]
            if not sender_email:
                raise EmailIngestionError("No sender address found")
            
            # Prepare email content
            email_subject = parsed["subject"] or "(No Subject)"
            email_body = parsed["body"] or ""
            
            # Check if email already exists (prevent duplicates)
            db = get_mongodb()
            existing = await db.emails.find_one({"email_id": token})
            
            if existing:
                logger.warning(f"Email with token {token[:16]}... already exists, skipping duplicate")
                return {
                    "email_id": token,
                    "status": "duplicate",
                    "message": "Email already exists",
                }
            
            # Encrypt and store email
            # Note: For incoming emails, we use authenticated mode (no passcode)
            # The token itself acts as the access key
            email_body_bytes = email_body.encode("utf-8")
            
            result = await self.email_service.encrypt_and_store_email(
                email_body=email_body_bytes,
                sender_email=sender_email,
                recipient_emails=[recipient_email],  # Store original recipient
                user_email=None,  # No authenticated user for incoming emails
                passcode=None,  # No passcode for incoming emails
                expires_in_hours=None,  # No expiration for incoming emails
                subject=email_subject,
                self_destruct=False,
                email_id=token,  # Use token as email_id
            )
            
            logger.info(f"Ingested email with token {token[:16]}... from {sender_email}")
            
            return {
                "email_id": token,
                "status": "ingested",
                "sender": sender_email,
                "recipient": recipient_email,
                "subject": email_subject[:50],  # Truncate for logging
            }
            
        except EmailIngestionError:
            raise
        except Exception as e:
            logger.error(f"Failed to ingest email: {e}", exc_info=True)
            raise EmailIngestionError(f"Failed to ingest email: {str(e)}") from e


# Global service instance
_email_ingestion_service: Optional[EmailIngestionService] = None


def get_email_ingestion_service() -> EmailIngestionService:
    """Get global email ingestion service instance"""
    global _email_ingestion_service
    if _email_ingestion_service is None:
        _email_ingestion_service = EmailIngestionService()
    return _email_ingestion_service
