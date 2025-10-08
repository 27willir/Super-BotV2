import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


def _get_bool_env(name: str, default: str = "True") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def send_email(subject: str, to_email: str, html_body: str, text_body: Optional[str] = None) -> bool:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM", user or "no-reply@example.com")
    use_tls = _get_bool_env("SMTP_USE_TLS", "True")

    if not host or not port or not from_email:
        # SMTP not configured; fail gracefully
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception:
        return False


def build_verification_email(app_name: str, to_email: str, verify_url: str) -> tuple[str, str]:
    subject = f"Verify your email for {app_name}"
    text = (
        f"Welcome to {app_name}!\n\n"
        f"Please verify your email by visiting this link:\n{verify_url}\n\n"
        f"If you did not sign up, you can ignore this email."
    )
    html = (
        f"<p>Welcome to <strong>{app_name}</strong>!</p>"
        f"<p>Please verify your email by clicking the link below:</p>"
        f"<p><a href=\"{verify_url}\">Verify Email</a></p>"
        f"<p>If you did not sign up, you can ignore this email.</p>"
    )
    return subject, html if html else text

