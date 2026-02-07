"""Gmail SMTP email sender."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from job_agent.config import EmailConfig

logger = logging.getLogger("job_agent.notifications")


def send_email(
    config: EmailConfig,
    subject: str,
    html_body: str,
) -> bool:
    """Send an HTML email via Gmail SMTP.

    Returns True on success, False on failure.
    """
    if not config.sender_email or not config.sender_password:
        logger.error("Email credentials not configured")
        return False

    if not config.recipient_email:
        logger.error("No recipient email configured")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.sender_email
    msg["To"] = config.recipient_email

    # Plain text fallback
    plain_text = f"View this email in an HTML-capable client.\n\nSubject: {subject}"
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.sender_email, config.sender_password)
            server.sendmail(config.sender_email, config.recipient_email, msg.as_string())

        logger.info("Email sent successfully to %s", config.recipient_email)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "SMTP authentication failed. Make sure you're using a Gmail App Password. "
            "See: https://support.google.com/accounts/answer/185833"
        )
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP error sending email: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error sending email: %s", e)
        return False
