# Super Bot

A web scraping automation bot for monitoring listings across multiple platforms (Facebook Marketplace, Craigslist, KSL).

## Project Structure

```
super-bot/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore rules
│
├── Core Modules
├── db.py                  # Database operations
├── security.py            # Security configuration
├── error_handling.py      # Error handling utilities
├── error_recovery.py      # Error recovery system
├── utils.py              # Utility functions
├── scraper_thread.py     # Scraper threading management
│
├── docs/                  # Documentation
│   ├── ANALYTICS_FEATURES.md
│   ├── ANALYTICS_PAGE_FIXES.md
│   ├── ERROR_HANDLING_IMPROVEMENTS.md
│   ├── SCRAPER_THREADING_FIXES.md
│   └── SECURITY_IMPROVEMENTS.md
│
├── scripts/               # Utility scripts
│   ├── init_db.py        # Initialize database
│   ├── create_user.py    # Create user accounts
│   └── scheduler.py      # Scraper scheduler
│
├── tests/                 # Test files
│   ├── test_db_integration.py
│   ├── test_password.py
│   ├── test_scraper_fixes.py
│   └── test_scraper_stability.py
│
├── scrapers/              # Scraper modules
│   ├── craigslist.py
│   ├── facebook.py
│   └── ksl.py
│
├── templates/             # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── settings.html
│   └── analytics.html
│
├── static/                # Static assets (CSS, JS, images)
├── logs/                  # Application logs
└── superbot.db           # SQLite database

```

## Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment:**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database:**
   ```bash
   python scripts/init_db.py
   ```

5. **Create a user:**
   ```bash
   python scripts/create_user.py <username> <password> <email>
   ```

## Running the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Notifications (Email & SMS)

This app can send notifications via email and SMS when new listings are found.

### Configure Providers

1. Copy `.env.example` to `.env` and fill in your provider credentials:

```bash
cp .env.example .env
```

Email (SMTP): set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` and either `SMTP_USE_TLS=true` or `SMTP_USE_SSL=true`.

SMS (Twilio): set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`.

2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Enable per-user notifications

1. Log in to the app and navigate to Settings (or the main Dashboard settings card).
2. Toggle "Email me" and/or "Text me".
3. Enter your phone number in E.164 format (e.g., `+15551234567`) for SMS.
4. Click "Send Test Notification" to validate configuration.

When scrapers discover a new matching listing, users with notifications enabled will receive an email and/or SMS with the listing details.

### CLI test (optional)

You can also test providers directly via the helper script:

```bash
TEST_TO_EMAIL=you@example.com TEST_TO_PHONE=+15551234567 python scripts/test_notifications.py
```

## Running Tests

```bash
# Test database integration
python tests/test_db_integration.py

# Test scraper functionality
python tests/test_scraper_fixes.py

# Test scraper stability
python tests/test_scraper_stability.py

# Test password hashing
python tests/test_password.py
```

## Features

- **Multi-platform scraping**: Facebook Marketplace, Craigslist, KSL
- **User authentication**: Secure login system with password hashing
- **Real-time monitoring**: Automated scraping with configurable intervals
- **Analytics dashboard**: Comprehensive analytics and insights
- **Error recovery**: Automatic error detection and recovery
- **Thread management**: Efficient multi-threaded scraper execution

## Security

- CSRF protection enabled
- Secure session management
- Password hashing with Werkzeug
- Environment variable support for sensitive data

## License

Private project - All rights reserved

