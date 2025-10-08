import random, re, time, json
import threading
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import urllib.parse
from pathlib import Path
from lxml import html
from utils import debug_scraper_output, logger
from db import get_settings, save_listing
from error_handling import ErrorHandler, log_errors, ScraperError, NetworkError
from notifications import notify_new_listing

# ======================
# CONFIGURATION
# ======================
ksl_url = "https://classifieds.ksl.com/search"
seen_listings = {}
_seen_listings_lock = threading.Lock()  # Thread safety for seen_listings

# ======================
# RUNNING FLAG
# ======================
running_flags = {"ksl": True}

# ======================
# HELPER FUNCTIONS
# ======================
def human_delay(flag_dict, flag_name, min_sec=1.5, max_sec=4.5):
    total = random.uniform(min_sec, max_sec)
    step = 0.25
    while total > 0 and flag_dict.get(flag_name, True):
        sleep_time = min(step, total)
        time.sleep(sleep_time)
        total -= sleep_time

def is_new_listing(link):
    with _seen_listings_lock:
        if link not in seen_listings:
            return True
        last_seen = seen_listings[link]
        return (datetime.now() - last_seen).total_seconds() > 86400

@log_errors()
def save_seen_listings(filename="ksl_seen.json"):
    """Save seen listings with timestamps to JSON."""
    try:
        with _seen_listings_lock:
            Path(filename).write_text(
                json.dumps({k: v.isoformat() for k, v in seen_listings.items()}, indent=2),
                encoding="utf-8"
            )
        logger.debug(f"Saved seen listings to {filename}")
    except (OSError, PermissionError) as e:
        logger.error(f"File system error saving seen listings: {e}")
        raise
    except Exception as e:
        logger.error(f"Error saving seen listings: {e}")
        raise

@log_errors()
def load_seen_listings(filename="ksl_seen.json"):
    """Load seen listings from JSON, if available."""
    global seen_listings
    try:
        text = Path(filename).read_text(encoding="utf-8")
        data = json.loads(text) if text else {}
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
        logger.error(f"Error loading seen listings: {e}")
        with _seen_listings_lock:
            seen_listings = {}

def send_discord_message(title, link, price=None, image_url=None):
    """Save listing to database and send notification."""
    try:
        # Save to database
        save_listing(title, price, link, image_url, "ksl")
        print(f"📢 New KSL: {title} | ${price} | {link}")
        try:
            notify_new_listing(title=title, link=link, price=price, image_url=image_url, source="ksl")
        except Exception as notify_err:
            logger.error(f"Failed to dispatch notifications for KSL listing {link}: {notify_err}")
    except Exception as e:
        print(f"⚠️ Failed to save listing for {link}: {e}")

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
# MAIN SCRAPER FUNCTION
# ======================
def check_ksl(flag_name="ksl"):
    settings = load_settings()
    keywords = settings["keywords"]
    min_price = settings["min_price"]
    max_price = settings["max_price"]
    check_interval = settings["interval"]

    results = []
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            base_url = "https://classifieds.ksl.com/search/"
            params = {
                "keyword": " ".join(keywords),
                "priceFrom": min_price,
                "priceTo": max_price,
            }
            full_url = base_url + "?" + urllib.parse.urlencode(params)

            response = requests.get(full_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            response.raise_for_status()  # Raise exception for bad status codes
            tree = html.fromstring(response.text)
            break  # Success, exit retry loop
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            logger.warning(f"KSL request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            else:
                logger.error(f"KSL request failed after {max_retries} attempts: {e}")
                return []
        except Exception as e:
            logger.error(f"Unexpected error in KSL scraper: {e}")
            return []

    # Process the results if we successfully got the page
    try:
        posts = tree.xpath('//section[contains(@class,"listing")]')
        for post in posts:
            try:
                link = post.xpath(".//a[@class='listing-item-link']/@href")[0]
                link = "https://classifieds.ksl.com" + link
                title = post.xpath(".//h2/text()")[0].strip()
                price = post.xpath(".//h3/text()")
                price_val = int(price[0].replace("$", "").replace(",", "")) if price else None

                if price_val and (price_val < min_price or price_val > max_price):
                    continue

                if any(k.lower() in title.lower() for k in keywords) and is_new_listing(link):
                    with _seen_listings_lock:
                        seen_listings[link] = datetime.now()
                    send_discord_message(title, link, price_val)
                    results.append({"title": title, "link": link, "price": price_val})
            except Exception as e:
                logger.warning(f"Error parsing a KSL post: {e}")

        if results:
            save_seen_listings()
        else:
            logger.info(f"No new KSL listings. Next check in {check_interval}s...")

        debug_scraper_output("KSL", results)
        return results

    except Exception as e:
        logger.error(f"Error processing KSL results: {e}")
        return []

# ======================
# CONTINUOUS RUNNER
# ======================
def run_ksl_scraper(flag_name="ksl"):
    """Run KSL scraper with proper error handling."""
    logger.info("Starting KSL scraper")
    load_seen_listings()
    
    try:
        while running_flags.get(flag_name, True):
            try:
                logger.debug("Running KSL scraper check")
                results = check_ksl()
                if results:
                    logger.info(f"KSL scraper found {len(results)} new listings")
                else:
                    logger.debug("KSL scraper found no new listings")
            except Exception as e:
                logger.error(f"Error in KSL scraper iteration: {e}")
                # Continue running but log the error
                continue
            
            settings = load_settings()
            human_delay(running_flags, flag_name, settings["interval"]*0.9, settings["interval"]*1.1)
            
    except KeyboardInterrupt:
        logger.info("KSL scraper interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in KSL scraper: {e}")
    finally:
        logger.info("KSL scraper stopped")
