import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from notifications import send_email, send_sms


def main():
    to_email = os.getenv("TEST_TO_EMAIL")
    to_phone = os.getenv("TEST_TO_PHONE")
    ok_email = False
    ok_sms = False
    if to_email:
        ok_email = send_email("Super Bot Test Email", "<p>Test email body</p>", to_email)
        print(f"Email result: {ok_email}")
    else:
        print("TEST_TO_EMAIL not set; skipping email test")

    if to_phone:
        ok_sms = send_sms("Super Bot test SMS", to_phone)
        print(f"SMS result: {ok_sms}")
    else:
        print("TEST_TO_PHONE not set; skipping SMS test")

    return 0 if (ok_email or ok_sms) else 1


if __name__ == "__main__":
    raise SystemExit(main())

