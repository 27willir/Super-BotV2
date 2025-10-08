import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import requests

from utils import logger
from db import get_all_users, get_settings


def _bool_from_str(value: Optional[str]) -> bool:
    if value is None:
        return False
    value_lower = str(value).strip().lower()
    return value_lower in {"1", "true", "yes", "on"}


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    return val if val is not None else default


def send_email(subject: str, body: str, to_email: str) -> bool:
    """Send an email using SMTP settings from environment variables.

    Required env vars:
      - SMTP_HOST
      - SMTP_PORT
      - SMTP_USER (optional if unauthenticated SMTP)
      - SMTP_PASSWORD (optional if unauthenticated SMTP)
      - SMTP_FROM (fallback to SMTP_USER)
      - SMTP_USE_TLS (default true) or SMTP_USE_SSL (default false)
    """
    host = _get_env("SMTP_HOST")
    port = _get_env("SMTP_PORT")
    user = _get_env("SMTP_USER")
    password = _get_env("SMTP_PASSWORD")
    from_email = _get_env("SMTP_FROM", user or "")
    use_tls = _bool_from_str(_get_env("SMTP_USE_TLS", "true"))
    use_ssl = _bool_from_str(_get_env("SMTP_USE_SSL", "false"))

    if not host or not port or not from_email:
        logger.warning("Email not sent: SMTP configuration incomplete")
        return False

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        port_int = int(port)
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port_int, timeout=20)
        else:
            server = smtplib.SMTP(host, port_int, timeout=20)
            if use_tls:
                server.starttls()

        if user and password:
            server.login(user, password)

        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        logger.info(f"Sent email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_sms(body: str, to_phone: str) -> bool:
    """Send an SMS using Twilio REST API with env configuration.

    Required env vars:
      - TWILIO_ACCOUNT_SID
      - TWILIO_AUTH_TOKEN
      - TWILIO_FROM_NUMBER
    """
    sid = _get_env("TWILIO_ACCOUNT_SID")
    token = _get_env("TWILIO_AUTH_TOKEN")
    from_number = _get_env("TWILIO_FROM_NUMBER")

    if not sid or not token or not from_number:
        logger.warning("SMS not sent: Twilio configuration incomplete")
        return False

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = {
        "From": from_number,
        "To": to_phone,
        "Body": body,
    }
    try:
        resp = requests.post(url, data=data, auth=(sid, token), timeout=20)
        if resp.status_code in (200, 201):
            logger.info(f"Sent SMS to {to_phone}")
            return True
        logger.error(f"Failed to send SMS to {to_phone}: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Exception sending SMS to {to_phone}: {e}")
        return False


def _build_listing_email_html(title: str, link: str, price: Optional[int], image_url: Optional[str], source: Optional[str]) -> str:
    price_str = f"${price:,}" if isinstance(price, int) else "N/A"
    image_block = f'<p><img src="{image_url}" alt="Listing image" width="300"/></p>' if image_url else ""
    source_str = source.capitalize() if source else "Listing"
    return (
        f"<h3>New {source_str} Listing</h3>"
        f"<p><strong>{title}</strong></p>"
        f"<p>Price: {price_str}</p>"
        f"<p><a href='{link}' target='_blank'>View Listing</a></p>"
        f"{image_block}"
    )


def _build_listing_sms_text(title: str, link: str, price: Optional[int], source: Optional[str]) -> str:
    price_str = f"${price:,}" if isinstance(price, int) else "N/A"
    source_str = source.capitalize() if source else "Listing"
    # Keep SMS concise to avoid splitting
    return f"{source_str}: {title} — {price_str} {link}"


def notify_new_listing(title: str, link: str, price: Optional[int] = None, image_url: Optional[str] = None, source: Optional[str] = None) -> None:
    """Broadcast a new listing notification to all opted-in users.

    Reads users from DB and checks per-user settings keys:
      - notify_email: bool
      - notify_sms: bool
      - phone_number: str
    Uses the user's stored email for email notifications.
    """
    try:
        users = get_all_users()
    except Exception as e:
        logger.error(f"notify_new_listing: failed to load users: {e}")
        return

    email_subject = f"New {source.capitalize() if source else 'Listing'}: {title}"
    email_html = _build_listing_email_html(title, link, price, image_url, source)
    sms_text = _build_listing_sms_text(title, link, price, source)

    for user in users:
        try:
            username, email, _, verified = user
            user_settings = get_settings(username)

            if _bool_from_str(user_settings.get("notify_email")) and email:
                send_email(email_subject, email_html, email)

            if _bool_from_str(user_settings.get("notify_sms")):
                phone = user_settings.get("phone_number")
                if phone:
                    send_sms(sms_text, phone)
        except Exception as e:
            logger.error(f"notify_new_listing: error notifying user {user}: {e}")


def send_test_notification(username: str, email: str) -> dict:
    """Send a test notification to a specific user based on their preferences."""
    settings = get_settings(username)
    results = {"email": False, "sms": False}

    # Email test
    if _bool_from_str(settings.get("notify_email")) and email:
        results["email"] = send_email(
            "Test Notification from Super Bot",
            "<p>This is a test email notification from Super Bot.</p>",
            email,
        )

    # SMS test
    if _bool_from_str(settings.get("notify_sms")):
        phone = settings.get("phone_number")
        if phone:
            results["sms"] = send_sms("Super Bot test SMS notification.", phone)

    return results

