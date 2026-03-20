"""Email security middleware - stubs."""


async def check_email_rate_limit(*args, **kwargs):
    return True


def validate_email_token(*args, **kwargs):
    return True


def validate_email_recipients(*args, **kwargs):
    return True


class EmailSecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)

    @staticmethod
    async def check_abuse_patterns(sender_email: str, recipients: list) -> None:
        """Stub - no-op for abuse pattern check."""
        pass

    @staticmethod
    async def log_email_send(*, user_email: str, recipients: list, email_id: str, success: bool) -> None:
        """Stub - no-op for email send logging."""
        pass

    @staticmethod
    def validate_email_size(size_bytes: int) -> None:
        """Stub - no-op for email size validation."""
        pass
