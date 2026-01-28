"""Email Sending Service

SMTP email sending service for sending encrypted emails via fxmail.ai domain.
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmailSender:
    """Service for sending emails via SMTP"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.email_domain = settings.EMAIL_DOMAIN
    
    async def send_email(
        self,
        from_email: str,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """
        Send an email via SMTP.
        
        Args:
            from_email: Sender email address
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
        
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = from_email
            message["To"] = ", ".join(to_emails)
            message["Subject"] = subject
            
            # Add plain text part
            text_part = MIMEText(body, "plain")
            message.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, "html")
                message.attach(html_part)
            
            # Send email with production-ready SMTP settings
            # Note: DKIM signing is handled by Postfix, not Python
            # SPF/DMARC are configured in DNS (Cloudflare)
            # For port 587, use STARTTLS (not use_tls which is for port 465 SSL)
            if self.smtp_port == 587:
                # Port 587 uses STARTTLS
                await aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_username if self.smtp_username else None,
                    password=self.smtp_password if self.smtp_password else None,
                    start_tls=self.smtp_use_tls,
                    timeout=30,  # 30 second timeout
                )
            elif self.smtp_port == 465:
                # Port 465 uses SSL/TLS directly
                await aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_username if self.smtp_username else None,
                    password=self.smtp_password if self.smtp_password else None,
                    use_tls=self.smtp_use_tls,
                    timeout=30,  # 30 second timeout
                )
            else:
                # Default: try STARTTLS for other ports
                await aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_username if self.smtp_username else None,
                    password=self.smtp_password if self.smtp_password else None,
                    start_tls=self.smtp_use_tls,
                    timeout=30,  # 30 second timeout
                )
            
            logger.info(f"Email sent from {from_email} to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False
    
    async def send_encrypted_email_notification(
        self,
        recipient_email: str,
        email_address: str,
        secure_link: str,
        sender_email: Optional[str] = None,
    ) -> bool:
        """
        Send notification email about encrypted email.
        
        Args:
            recipient_email: Recipient email address
            email_address: Generated email address (e.g., token@fxmail.ai)
            secure_link: Secure link to access encrypted email
            sender_email: Optional sender email address
        
        Returns:
            True if notification sent successfully
        """
        subject = "You have received an encrypted email"
        
        # Plain text body
        body = f"""You have received an encrypted email.

To view this email, click on the secure link below:
{secure_link}

This link will allow you to access the encrypted email securely.

If you did not expect this email, please ignore it.
"""
        
        # HTML body
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .button:hover {{ background-color: #0056b3; }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>You have received an encrypted email</h2>
        <p>To view this email securely, click on the button below:</p>
        <a href="{secure_link}" class="button">View Encrypted Email</a>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #007bff;">{secure_link}</p>
        <div class="footer">
            <p>This is an automated notification from fxmail.ai</p>
            <p>If you did not expect this email, please ignore it.</p>
        </div>
    </div>
</body>
</html>
"""
        
        from_email = email_address  # Use generated email address as sender
        
        return await self.send_email(
            from_email=from_email,
            to_emails=[recipient_email],
            subject=subject,
            body=body,
            html_body=html_body,
        )


# Global email sender instance
_email_sender: Optional[EmailSender] = None


def get_email_sender() -> EmailSender:
    """Get global email sender instance"""
    global _email_sender
    if _email_sender is None:
        _email_sender = EmailSender()
    return _email_sender
