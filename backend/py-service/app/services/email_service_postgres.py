"""PostgreSQL email service - stub for migration. Full implementation TBD."""

from typing import Optional, Dict, Any, List


class EmailEncryptionError(Exception):
    pass


class EmailServicePostgres:
    """PostgreSQL email service - minimal stub."""

    async def encrypt_and_store_email(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Email service migration in progress. Use drive for now.")

    async def decrypt_email_for_authenticated_user(self, **kwargs):
        raise NotImplementedError("Email service migration in progress.")

    async def decrypt_email_with_passcode(self, **kwargs):
        raise NotImplementedError("Email service migration in progress.")

    async def delete_email(self, email_id: str) -> bool:
        return False

    async def get_inbox_emails(self, user_email: str) -> List[Dict]:
        return []

    async def get_sent_emails(self, user_email: str) -> List[Dict]:
        return []

    async def get_draft_emails(self, user_email: str) -> List[Dict]:
        return []


def get_email_service_mongodb() -> EmailServicePostgres:
    return EmailServicePostgres()
