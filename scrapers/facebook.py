import random, re, time, json
import urllib.parse
import threading
from datetime import datetime
from lxml import html
from selenium.webdriver.common.by import By
from utils import debug_scraper_output, logger
from db import get_settings, save_listing
from error_handling import ErrorHandler, log_errors, ScraperError, NetworkError

# ======================
# CONFIGURATION
# ======================
facebook_url = "https://www.facebook.com/marketplace/108420222512131/?radius_in_km=402"
seen_listings = {}
_seen_listings_lock = threading.Lock()  # Thread safety for seen_listings

# ======================
# RUNNING FLAG
# ======================
running_flags = {"facebook": True}

# ======================
# HELPER FUNCTIONS
# ======================
def human_delay(flag_dict, flag_name, min_sec=1.5, max_sec=4.5):
    """Pause between requests with human-like randomness, respecting stop flags."""
    total = random.uniform(min_sec, max_sec)
    step = 0.25  # smaller step for faster stop response
    while total > 0 and flag_dict.get(flag_name, True):
        sleep_time = min(step, total)
        time.sleep(sleep_time)
        total -= sleep_time

def human_scroll(driver, flag_dict, flag_name, min_scrolls=1, max_scrolls=3):
    """Simulate human scrolling behavior, stopping if flag is cleared."""
    for _ in range(random.randint(min_scrolls, max_scrolls)):
        if not flag_dict.get(flag_name, True):
            break
        driver.execute_script("window.scrollBy(0, 600);")
        human_delay(flag_dict, flag_name, min_sec=1, max_sec=2)

def is_new_listing(link):
    """Check if a listing has been seen within the last 24 hours."""
    with _seen_listings_lock:
        if link not in seen_listings:
            return True
        last_seen = seen_listings[link]
        return (datetime.now() - last_seen).total_seconds() > 86400

@log_errors()
def save_seen_listings(filename="seen_listings.json"):
    """Save seen listings to JSON."""
    try:
        with _seen_listings_lock:
            with open(filename, "w") as f:
                json.dump({k: v.isoformat() for k, v in seen_listings.items()}, f)
        logger.debug(f"Saved seen listings to {filename}")
    except (OSError, PermissionError) as e:
        logger.error(f"File system error saving seen listings: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to save seen listings: {e}")
        raise

@log_errors()
def load_seen_listings(filename="seen_listings.json"):
    """Load previously seen listings from JSON."""
    global seen_listings
    try:
        with open(filename, "r") as f:
            data = json.load(f)
        with _seen_listings_lock:
            seen_listings = {k: datetime.fromisoformat(v) for k, v in data.items()}
        logger.debug(f"Loaded {len(seen_listings)} seen listings from {filename}")
    except FileNotFoundError:
        logger.info(f"Seen listings file not found: {filename}, starting fresh")
        with _seen_listings_lock:
            seen_listings = {}
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid JSON in seen listings file: {e}")
        with _seen_listings_lock:
            seen_listings = {}
    except Exception as e:
        logger.error(f"Failed to load seen listings: {e}")
        with _seen_listings_lock:
            seen_listings = {}

@log_errors()
def send_discord_message(title, link, price=None, image_url=None):
    """Save listing to database and send notification."""
    try:
        # Save to database
        ErrorHandler.handle_database_error(save_listing, title, price, link, image_url, "facebook")
        logger.info(f"📢 New Facebook Listing: {title} | ${price} | {link}")
    except Exception as e:
        logger.error(f"Failed to save Facebook listing for {link}: {e}")
        raise

def load_settings():
    """Load settings from database"""
    try:
        settings = get_settings()  # Get global settings
        return {
            "keywords": [k.strip() for k in settings.get("keywords","Firebird,Camaro,Corvette").split(",") if k.strip()],
            "min_price": int(settings.get("min_price", 1000)),
            "max_price": int(settings.get("max_price", 30000)),
            "interval": int(settings.get("interval", 60)),
            "location": settings.get("location", "boise"),
            "radius": int(settings.get("radius", 50))
        }
    except Exception as e:
        print(f"⚠️ Failed to load settings: {e}")
        return {
            "keywords": ["Firebird","Camaro","Corvette"],
            "min_price": 1000,
            "max_price": 30000,
            "interval": 60,
            "location": "boise",
            "radius": 50
        }

# ======================
# DYNAMIC FACEBOOK URL
# ======================
import urllib.parse

def get_facebook_url(settings):
    """
    Build the Marketplace URL based on current settings.
    """
    base_url = "https://www.facebook.com/marketplace/108420222512131/"
    location = settings.get("location", "boise")
    radius = settings.get("radius", 402)  # default radius

    # Ensure radius is a string
    return f"{base_url}?query={urllib.parse.quote(location)}&radius_in_km={str(radius)}"

# ======================
# MAIN SCRAPER FUNCTION
# ======================
@log_errors()
def check_facebook(driver):
    try:
        settings = ErrorHandler.handle_database_error(load_settings)
        keywords = settings["keywords"]
        min_price = settings["min_price"]
        max_price = settings["max_price"]
        check_interval = settings["interval"]

        url = get_facebook_url(settings)  # dynamically generate URL

        # Navigate to page with network error handling
        ErrorHandler.handle_network_error(lambda: driver.get(url))
        human_delay(running_flags, "facebook", min_sec=3, max_sec=6)
        human_scroll(driver, running_flags, "facebook")

        tree = html.fromstring(driver.page_source)
        anchors = [a for a in tree.xpath("//a[@href]") if isinstance(a.get("href"), str)]

        new_links = []
        for a in anchors:
            try:
                link = a.get("href").split("?")[0].strip()
                title = (a.text_content() or "").strip()

                if not title or not link:
                    continue

                # Extract price from title
                price = None
                price_match = re.search(r"\$\s?([\d,]+)", title)
                if price_match:
                    try:
                        price = int(price_match.group(1).replace(",", ""))
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Could not parse price from title '{title}': {e}")
                        price = None

                if price is not None and (price < min_price or price > max_price):
                    continue

                # Check keywords and if new
                if any(keyword.lower() in title.lower() for keyword in keywords) and is_new_listing(link):
                    with _seen_listings_lock:
                        seen_listings[link] = datetime.now()

                    # Attempt to get image URL
                    image_url = None
                    try:
                        elem = driver.find_element(By.XPATH, f"//a[@href='{link}']//img")
                        image_url = elem.get_attribute("src")
                    except Exception as e:
                        logger.debug(f"Could not extract image URL for {link}: {e}")

                    send_discord_message(title, link, price, image_url)
                    new_links.append(link)
            except Exception as e:
                logger.warning(f"Error processing Facebook listing: {e}")
                continue

        if new_links:
            save_seen_listings()
        else:
            logger.debug(f"No new Facebook listings. Next check in {check_interval}s...")

        debug_scraper_output("Facebook", new_links)
        return new_links

    except NetworkError as e:
        logger.error(f"Network error scraping Facebook: {e}")
        return []
    except ScraperError as e:
        logger.error(f"Scraper error on Facebook: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error scraping Facebook: {e}")
        return []

# ======================
# CONTINUOUS RUNNER
# ======================
@log_errors()
def run_facebook_scraper(driver, flag_name="facebook"):
    """Run Facebook scraper with proper error handling and timeout protection."""
    try:
        load_seen_listings()
        logger.info("Starting Facebook scraper")
        
        while running_flags.get(flag_name, True):
            try:
                check_facebook(driver)
            except NetworkError as e:
                logger.error(f"Network error in Facebook scraper iteration: {e}")
                # Wait longer before retry on network errors
                human_delay(running_flags, flag_name, 30, 60)
                continue
            except ScraperError as e:
                logger.error(f"Scraper error in Facebook iteration: {e}")
                # Continue running but log the error
                continue
            except Exception as e:
                logger.error(f"Unexpected error in Facebook scraper iteration: {e}")
                continue
            
            try:
                settings = ErrorHandler.handle_database_error(load_settings)
                human_delay(running_flags, flag_name, settings["interval"]*0.9, settings["interval"]*1.1)
            except Exception as e:
                logger.error(f"Error in Facebook scraper delay: {e}")
                # Use default delay if settings fail
                human_delay(running_flags, flag_name, 60, 90)
            
    except KeyboardInterrupt:
        logger.info("🛑 Facebook scraper interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error in Facebook scraper: {e}")
    finally:
        logger.info("🛑 Facebook scraper stopped")
