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
