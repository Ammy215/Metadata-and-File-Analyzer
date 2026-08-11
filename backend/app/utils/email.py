import logging
import resend

from app.config import settings

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, otp_code: str) -> None:
    """Send a 6-digit verification code to to_email via Resend.

    Falls back to logging the code server-side when RESEND_API_KEY isn't
    configured, so local dev works without a real key (same convention as
    GOOGLE_CLIENT_ID). Never raises - a delivery failure shouldn't break
    registration, since the user can always request a resend.
    """
    if not settings.RESEND_API_KEY or settings.RESEND_API_KEY == "NOT_CONFIGURED_OPTIONAL":
        logger.info(f"[DEV] RESEND_API_KEY not set - OTP for {to_email} is: {otp_code}")
        return

    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": "Verify your FileShield account",
            "html": (
                f"<p>Your FileShield verification code is:</p>"
                f"<h2 style='letter-spacing: 4px;'>{otp_code}</h2>"
                f"<p>This code expires in 10 minutes.</p>"
            ),
        })
    except Exception as e:
        logger.error(f"Failed to send OTP email to {to_email}: {e}")
