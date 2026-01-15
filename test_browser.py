#!/usr/bin/env python3
"""Test if browser can launch"""
import asyncio
from linkedin_scraper import BrowserManager

async def test():
    print("[*] Testing browser launch...")
    print("[*] Creating BrowserManager with headless=False...")
    async with BrowserManager(headless=False) as browser:
        print("[OK] Browser context created")
        print(f"[*] Browser headless: {browser.headless}")
        print("[*] Navigating to LinkedIn...")
        await browser.page.goto("https://www.linkedin.com/login")
        print("[OK] Navigated to LinkedIn login page")
        print("[*] Browser should be visible now. Waiting 10 seconds...")
        await asyncio.sleep(10)
        print("[OK] Test complete")

if __name__ == "__main__":
    asyncio.run(test())


