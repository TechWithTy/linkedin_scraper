#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn Scraper Wrapper
Wrapper script for scraping LinkedIn profiles, companies, and jobs
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import subprocess

try:
    from linkedin_scraper import (
        BrowserManager,
        PersonScraper,
        CompanyScraper,
        JobSearchScraper,
        wait_for_manual_login,
        login_with_credentials,
    )
except ImportError as e:
    print(f"[X] Error: Missing required package: {e}")
    print("[!] Please install dependencies: cd submodules/linkedin-scraper && ./setup-venv.sh")
    sys.exit(1)

# Import cookie extraction if available
try:
    from extract_linkedin_cookies import extract_linkedin_cookies
except ImportError:
    extract_linkedin_cookies = None


async def create_session_from_cookies(
    cookie_file: str,
    session_file: str = "linkedin_session.json",
    headless: bool = True,
):
    """Create a LinkedIn session from extracted cookies"""
    print(f"[*] Creating LinkedIn session from cookies: {cookie_file}")
    
    if not Path(cookie_file).exists():
        print(f"[X] Error: Cookie file not found: {cookie_file}")
        return False
    
    # Load cookies from JSON file
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        print(f"[OK] Loaded {len(cookies)} cookie(s) from {cookie_file}")
    except Exception as e:
        print(f"[X] Error loading cookies: {e}")
        return False
    
    # Check for authentication cookies
    auth_cookie_names = ['li_at', 'JSESSIONID', 'bcookie', 'bscookie']
    found_auth = any(c.get('name') in auth_cookie_names for c in cookies)
    if not found_auth:
        print(f"[!] Warning: No authentication cookies found in cookie file")
        print(f"[!] Session may not work properly")
    
    async with BrowserManager(headless=headless, slow_mo=100) as browser:
        # Navigate to LinkedIn first
        await browser.page.goto("https://www.linkedin.com")
        
        # Add cookies to browser context
        # Convert cookie format to Playwright format
        playwright_cookies = []
        for cookie in cookies:
            pw_cookie = {
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie.get('domain', '.linkedin.com'),
                'path': cookie.get('path', '/'),
            }
            if cookie.get('expiry'):
                pw_cookie['expires'] = cookie['expiry']
            if cookie.get('secure'):
                pw_cookie['secure'] = cookie['secure']
            if cookie.get('httpOnly'):
                pw_cookie['httpOnly'] = cookie['httpOnly']
            playwright_cookies.append(pw_cookie)
        
        await browser.context.add_cookies(playwright_cookies)
        print(f"[OK] Injected {len(playwright_cookies)} cookie(s) into browser")
        
        # Refresh page to apply cookies
        await browser.page.reload()
        await asyncio.sleep(2)
        
        # Verify authentication by checking if we're logged in
        current_url = browser.page.url
        if 'login' in current_url.lower() or 'authwall' in current_url.lower():
            print(f"[!] Warning: Still on login page - cookies may be invalid or expired")
            print(f"[!] Current URL: {current_url}")
            return False
        
        # Navigate to feed to verify authentication
        await browser.page.goto("https://www.linkedin.com/feed")
        await asyncio.sleep(2)
        
        # Check if we're authenticated
        final_url = browser.page.url
        if 'login' in final_url.lower() or 'authwall' in final_url.lower():
            print(f"[X] Error: Authentication failed - still redirected to login")
            print(f"[X] Cookies may be expired or invalid")
            return False
        
        print(f"[OK] Authentication verified - logged in successfully")
        
        # Save session
        await browser.save_session(session_file)
        print(f"[OK] Session saved to {session_file}")
        return True


async def create_session(
    session_file: str = "linkedin_session.json",
    headless: bool = False,
    cookie_file: Optional[str] = None,
):
    """Create a LinkedIn session by manual login or from cookies"""
    if cookie_file:
        # Use cookie-based session creation
        success = await create_session_from_cookies(cookie_file, session_file, headless)
        if not success:
            print(f"[!] Cookie-based session creation failed")
            print(f"[!] Falling back to manual login...")
            # Fall through to manual login
        else:
            return
    
    # Manual login (default)
    print("[*] Creating LinkedIn session via manual login...")
    print(f"[*] Headless mode: {headless}")
    if not headless:
        print("[*] Browser will open - please log in manually")
        print("[*] IMPORTANT: Complete the login process in the browser window")
        print("[*] The script will wait for you to log in successfully...")
    else:
        print("[!] WARNING: Headless mode is enabled. Browser window will NOT be visible!")
        print("[!] For manual login, you MUST use --no-headless flag")
        # Force headless=False for manual login
        headless = False
    
    async with BrowserManager(headless=headless, slow_mo=100) as browser:
        await browser.page.goto("https://www.linkedin.com/login")
        print("[*] Waiting for manual login (timeout: 10 minutes)...")
        print("[*] Please log in to LinkedIn in the browser window that opened")
        print("[*] The browser window should be visible - complete the login process there")
        try:
            # Timeout is in milliseconds: 10 minutes = 600000 ms
            await wait_for_manual_login(browser.page, timeout=600000)
        except Exception as e:
            print(f"[X] Error during login: {e}")
            print("[!] Please try again and make sure to complete the login process")
            raise
        
        await browser.save_session(session_file)
        print(f"[OK] Session saved to {session_file}")
        print("[OK] You can now use this session file for scraping")


async def scrape_person(
    profile_url: str,
    session_file: str = "linkedin_session.json",
    output_file: Optional[str] = None,
    headless: bool = True,
):
    """Scrape a LinkedIn person profile"""
    print(f"[*] Scraping person profile: {profile_url}")
    
    async with BrowserManager(headless=headless) as browser:
        # Load session
        if Path(session_file).exists():
            await browser.load_session(session_file)
            print(f"[OK] Loaded session from {session_file}")
        else:
            print(f"[!] Session file not found: {session_file}")
            print("[!] Please create a session first or log in manually")
            return
        
        # Create scraper
        scraper = PersonScraper(browser.page)
        
        # Scrape profile
        try:
            person = await scraper.scrape(profile_url)
            
            # Convert to dict for JSON serialization
            person_data = {
                "name": person.name,
                "headline": person.headline,
                "location": person.location,
                "about": person.about,
                "linkedin_url": person.linkedin_url,
                "experiences": [
                    {
                        "title": exp.title,
                        "company": exp.company,
                        "location": exp.location,
                        "description": exp.description,
                        "start_date": exp.start_date,
                        "end_date": exp.end_date,
                        "duration": exp.duration,
                    }
                    for exp in person.experiences
                ],
                "educations": [
                    {
                        "school": edu.school,
                        "degree": edu.degree,
                        "field_of_study": edu.field_of_study,
                        "start_date": edu.start_date,
                        "end_date": edu.end_date,
                    }
                    for edu in person.educations
                ],
                "skills": person.skills,
                "scraped_at": datetime.now().isoformat(),
            }
            
            # Save to file
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"linkedin_person_{timestamp}.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(person_data, f, indent=2, ensure_ascii=False)
            
            print(f"[OK] Profile data saved to {output_file}")
            print(f"[*] Name: {person_data['name']}")
            print(f"[*] Headline: {person_data['headline']}")
            print(f"[*] Location: {person_data['location']}")
            print(f"[*] Experiences: {len(person_data['experiences'])}")
            print(f"[*] Education: {len(person_data['educations'])}")
            print(f"[*] Skills: {len(person_data['skills'])}")
            
        except Exception as e:
            print(f"[X] Error scraping profile: {e}")
            raise


async def scrape_company(
    company_url: str,
    session_file: str = "linkedin_session.json",
    output_file: Optional[str] = None,
    headless: bool = True,
):
    """Scrape a LinkedIn company page"""
    print(f"[*] Scraping company: {company_url}")
    
    async with BrowserManager(headless=headless) as browser:
        # Load session
        if Path(session_file).exists():
            await browser.load_session(session_file)
            print(f"[OK] Loaded session from {session_file}")
        else:
            print(f"[!] Session file not found: {session_file}")
            print("[!] Please create a session first or log in manually")
            return
        
        # Create scraper
        scraper = CompanyScraper(browser.page)
        
        # Scrape company
        try:
            company = await scraper.scrape(company_url)
            
            # Convert to dict for JSON serialization
            company_data = {
                "name": company.name,
                "industry": company.industry,
                "company_size": company.company_size,
                "headquarters": company.headquarters,
                "founded": company.founded,
                "specialties": company.specialties,
                "about": company.about_us,
                "linkedin_url": company.linkedin_url,
                "scraped_at": datetime.now().isoformat(),
            }
            
            # Save to file
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"linkedin_company_{timestamp}.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(company_data, f, indent=2, ensure_ascii=False)
            
            print(f"[OK] Company data saved to {output_file}")
            print(f"[*] Company: {company_data['name']}")
            print(f"[*] Industry: {company_data['industry']}")
            print(f"[*] Size: {company_data['company_size']}")
            print(f"[*] Headquarters: {company_data['headquarters']}")
            
        except Exception as e:
            print(f"[X] Error scraping company: {e}")
            raise


async def search_jobs(
    keywords: str,
    location: Optional[str] = None,
    limit: int = 10,
    session_file: str = "linkedin_session.json",
    output_file: Optional[str] = None,
    headless: bool = True,
):
    """Search for LinkedIn jobs"""
    print(f"[*] Searching jobs: keywords='{keywords}', location='{location}', limit={limit}")
    
    async with BrowserManager(headless=headless) as browser:
        # Load session
        if Path(session_file).exists():
            await browser.load_session(session_file)
            print(f"[OK] Loaded session from {session_file}")
        else:
            print(f"[!] Session file not found: {session_file}")
            print("[!] Please create a session first or log in manually")
            return
        
        # Create scraper
        scraper = JobSearchScraper(browser.page)
        
        # Search jobs
        try:
            jobs = await scraper.search(
                keywords=keywords,
                location=location,
                limit=limit,
            )
            
            # Convert to list of dicts for JSON serialization
            jobs_data = [
                {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "description": job.description,
                    "employment_type": job.employment_type,
                    "seniority_level": job.seniority_level,
                    "linkedin_url": job.linkedin_url,
                }
                for job in jobs
            ]
            
            result = {
                "keywords": keywords,
                "location": location,
                "total_results": len(jobs_data),
                "jobs": jobs_data,
                "scraped_at": datetime.now().isoformat(),
            }
            
            # Save to file
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"linkedin_jobs_{timestamp}.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"[OK] Job search results saved to {output_file}")
            print(f"[*] Found {len(jobs_data)} jobs")
            
        except Exception as e:
            print(f"[X] Error searching jobs: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Scraper Wrapper")
    parser.add_argument("--mode", choices=["person", "company", "jobs", "session", "multiple"], required=True,
                       help="Scraping mode")
    parser.add_argument("--url", help="Profile or company URL (for person/company mode)")
    parser.add_argument("--urls", help="Comma-separated list of profile URLs (for multiple mode)")
    parser.add_argument("--keywords", help="Job search keywords (for jobs mode)")
    parser.add_argument("--location", help="Job search location (for jobs mode)")
    parser.add_argument("--limit", type=int, default=10, help="Limit for job search (default: 10)")
    parser.add_argument("--session", default="linkedin_session.json", help="Session file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Show browser window")
    parser.add_argument("--cookies", help="Cookie file path (for automatic session creation)")
    parser.add_argument("--cookie-file", dest="cookies", help="Alias for --cookies")
    parser.add_argument("--mock", action="store_true", help=argparse.SUPPRESS)  # Hidden flag
    
    args = parser.parse_args()
    
    # If mock mode, use mock scraper
    if args.mock:
        try:
            from linkedin_scraper_mock import (
                mock_scrape_person,
                mock_scrape_company,
                mock_search_jobs,
                mock_scrape_multiple_profiles,
            )
            
            if args.mode == "person":
                if not args.url:
                    print("[X] Error: --url is required for person mode")
                    sys.exit(1)
                asyncio.run(mock_scrape_person(args.url, args.output))
            elif args.mode == "multiple":
                if not args.urls:
                    print("[X] Error: --urls is required for multiple mode")
                    sys.exit(1)
                urls = [url.strip() for url in args.urls.split(",")]
                asyncio.run(mock_scrape_multiple_profiles(urls, args.output))
            elif args.mode == "company":
                if not args.url:
                    print("[X] Error: --url is required for company mode")
                    sys.exit(1)
                asyncio.run(mock_scrape_company(args.url, args.output))
            elif args.mode == "jobs":
                if not args.keywords:
                    print("[X] Error: --keywords is required for jobs mode")
                    sys.exit(1)
                asyncio.run(mock_search_jobs(args.keywords, args.location, args.limit, args.output))
            elif args.mode == "session":
                print("[X] Error: Mock mode does not support session creation")
                sys.exit(1)
            return
        except ImportError as e:
            print(f"[X] Error: Could not import mock scraper: {e}")
            sys.exit(1)
    
    if args.mode == "session":
        # For session creation, always use non-headless (manual login requires visible browser)
        # But respect --headless flag if explicitly set (though it doesn't make sense for manual login)
        session_headless = args.headless
        if session_headless:
            print("[!] WARNING: Session creation with headless=True doesn't make sense for manual login")
            print("[!] Forcing headless=False for session creation")
            session_headless = False
        asyncio.run(create_session(args.session, headless=session_headless))
    elif args.mode == "person":
        if not args.url:
            print("[X] Error: --url is required for person mode")
            sys.exit(1)
        asyncio.run(scrape_person(args.url, args.session, args.output, args.headless))
    elif args.mode == "company":
        if not args.url:
            print("[X] Error: --url is required for company mode")
            sys.exit(1)
        asyncio.run(scrape_company(args.url, args.session, args.output, args.headless))
    elif args.mode == "jobs":
        if not args.keywords:
            print("[X] Error: --keywords is required for jobs mode")
            sys.exit(1)
        asyncio.run(search_jobs(args.keywords, args.location, args.limit, args.session, args.output, args.headless))


if __name__ == "__main__":
    main()

