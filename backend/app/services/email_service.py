"""
Email service using Resend for transactional emails.

Handles password reset emails with brutalist-themed HTML templates.
"""

import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_email_service():
    """Initialize Resend API key if configured."""
    if settings.RESEND_API_KEY:
        resend.api_key = settings.RESEND_API_KEY
        logger.info("Resend email configured successfully")
    else:
        logger.warning(
            "RESEND_API_KEY not set - password reset emails will not work"
        )


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    """Send password reset email via Resend."""
    if not settings.RESEND_API_KEY:
        logger.error(
            "Cannot send password reset email - RESEND_API_KEY not configured"
        )
        return False

    reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}"

    # Minimal brutalist email template (exact copy from server.py)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'DM Sans', Arial, sans-serif; background: #F7F7F7; padding: 40px 20px; }}
            .container {{ max-width: 500px; margin: 0 auto; background: #fff; border: 2px solid #0F0F0F; padding: 40px; }}
            h1 {{ font-family: 'Bebas Neue', Arial, sans-serif; font-size: 28px; letter-spacing: 2px; text-transform: uppercase; margin: 0 0 20px 0; }}
            p {{ color: #333; line-height: 1.6; margin: 0 0 20px 0; }}
            .button {{ display: inline-block; background: #F97316; color: #fff; text-decoration: none; padding: 14px 28px; border: 2px solid #0F0F0F; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 2px solid #0F0F0F; font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>RESET YOUR PASSWORD</h1>
            <p>You requested a password reset for your Arivu account. Click the button below to set a new password.</p>
            <p><a href="{reset_url}" class="button">RESET PASSWORD</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this, you can safely ignore this email.</p>
            <div class="footer">ARIVU — YOUR AI-POWERED SECOND BRAIN</div>
        </div>
    </body>
    </html>
    """

    try:
        params = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [email],
            "subject": "Reset Your Arivu Password",
            "html": html_content,
        }
        resend.Emails.send(params)
        logger.info(f"Password reset email sent to {email}")
        return True
    except Exception as e:
        logger.exception("Failed to send password reset email")
        return False


# Initialize on import
init_email_service()
