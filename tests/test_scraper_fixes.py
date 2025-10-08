#!/usr/bin/env python3
"""
Test script to verify scraper fixes are working properly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.craigslist import check_craigslist
from scrapers.ksl import check_ksl
from utils import logger

def test_craigslist_scraper():
    """Test Craigslist scraper functionality."""
    print("Testing Craigslist scraper...")
    try:
        results = check_craigslist()
        print(f"✅ Craigslist scraper completed successfully. Found {len(results)} listings.")
        return True
    except Exception as e:
        print(f"❌ Craigslist scraper failed: {e}")
        return False

def test_ksl_scraper():
    """Test KSL scraper functionality."""
    print("Testing KSL scraper...")
    try:
        results = check_ksl()
        print(f"✅ KSL scraper completed successfully. Found {len(results)} listings.")
        return True
    except Exception as e:
        print(f"❌ KSL scraper failed: {e}")
        return False

def main():
    """Run all scraper tests."""
    print("🔍 Testing scraper fixes...")
    print("=" * 50)
    
    craigslist_ok = test_craigslist_scraper()
    print()
    ksl_ok = test_ksl_scraper()
    
    print("=" * 50)
    if craigslist_ok and ksl_ok:
        print("✅ All scrapers are working correctly!")
        return 0
    else:
        print("❌ Some scrapers are still having issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
