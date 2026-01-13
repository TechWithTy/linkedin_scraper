#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn Cookie Extractor
Automatically extracts LinkedIn cookies from browser cookie databases
Supports Firefox, Chrome, and Edge browsers
Similar to extract_bumble_cookies.py and extract_tinder_cookies.py
"""

from argparse import ArgumentParser
from glob import glob
from os.path import expanduser, exists
from platform import system
from sqlite3 import OperationalError, connect
import json
import sys

# Color output (simple ASCII for cross-platform compatibility)
GREEN = "[OK]"
RED = "[X]"
YELLOW = "[!]"
CYAN = "[*]"

# LinkedIn authentication cookie names
LINKEDIN_AUTH_COOKIES = ['li_at', 'JSESSIONID', 'bcookie', 'bscookie', 'lang', 'li_rm']


def has_linkedin_cookies(cookiefile, is_firefox=True):
    """Check if a cookie file contains LinkedIn cookies."""
    try:
        if is_firefox:
            conn = connect(f"file:{cookiefile}?immutable=1", uri=True)
            try:
                # Try modern Firefox cookie schema first - check for LinkedIn cookies
                result = conn.execute(
                    "SELECT COUNT(*) FROM moz_cookies WHERE (baseDomain='linkedin.com' OR baseDomain='.linkedin.com')"
                ).fetchone()
                if result and result[0] > 0:
                    return True
            except OperationalError:
                # Fallback to host-based query
                result = conn.execute(
                    "SELECT COUNT(*) FROM moz_cookies WHERE host LIKE '%linkedin.com'"
                ).fetchone()
                if result and result[0] > 0:
                    return True
        else:
            # Chrome/Edge cookie schema
            conn = connect(f"file:{cookiefile}?immutable=1", uri=True)
            result = conn.execute(
                "SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%linkedin.com'"
            ).fetchone()
            if result and result[0] > 0:
                return True
        conn.close()
    except Exception:
        # Silently fail - don't print warnings during discovery
        pass
    return False


def get_firefox_cookie_files():
    """Get Firefox cookie files, checking both regular Firefox and Firefox Developer Edition."""
    platform = system()
    
    # Define all possible Firefox profile locations
    if platform == "Windows":
        cookie_patterns = [
            "~/AppData/Roaming/Mozilla/Firefox/Profiles/*/cookies.sqlite",
            "~/AppData/Roaming/Mozilla/Firefox Developer Edition/Profiles/*/cookies.sqlite",
        ]
    elif platform == "Darwin":  # macOS
        cookie_patterns = [
            "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite",
            "~/Library/Application Support/Firefox Developer Edition/Profiles/*/cookies.sqlite",
        ]
    else:  # Linux
        cookie_patterns = [
            "~/.mozilla/firefox/*/cookies.sqlite",
            "~/.mozilla/firefox-developer-edition/*/cookies.sqlite",
        ]
    
    # Collect all cookie files from all locations
    all_cookiefiles = []
    for pattern in cookie_patterns:
        found_files = glob(expanduser(pattern))
        all_cookiefiles.extend(found_files)
    
    if not all_cookiefiles:
        return []
    
    # Prioritize cookie files that contain LinkedIn cookies
    prioritized = []
    others = []
    
    for cookiefile in all_cookiefiles:
        if has_linkedin_cookies(cookiefile, is_firefox=True):
            prioritized.append(cookiefile)
        else:
            others.append(cookiefile)
    
    return prioritized + others


def get_chrome_cookie_files():
    """Get Chrome cookie files from all profile directories."""
    platform = system()
    
    if platform == "Windows":
        base_paths = [
            "~/AppData/Local/Google/Chrome/User Data",
        ]
    elif platform == "Darwin":  # macOS
        base_paths = [
            "~/Library/Application Support/Google/Chrome",
        ]
    else:  # Linux
        base_paths = [
            "~/.config/google-chrome",
        ]
    
    cookie_files = []
    for base_path in base_paths:
        expanded_base = expanduser(base_path)
        if not exists(expanded_base):
            continue
        
        # Check Default profile first
        default_cookies = expanduser(f"{base_path}/Default/Cookies")
        if exists(default_cookies):
            cookie_files.append(default_cookies)
        
        # Check other profiles
        profile_pattern = expanduser(f"{base_path}/Profile */Cookies")
        cookie_files.extend(glob(profile_pattern))
        
        # Also check numbered profiles
        numbered_pattern = expanduser(f"{base_path}/Profile [0-9]*/Cookies")
        cookie_files.extend(glob(numbered_pattern))
    
    # Prioritize cookie files that contain LinkedIn cookies
    prioritized = []
    others = []
    
    for cookiefile in cookie_files:
        if has_linkedin_cookies(cookiefile, is_firefox=False):
            prioritized.append(cookiefile)
        else:
            others.append(cookiefile)
    
    return prioritized + others


def get_edge_cookie_files():
    """Get Edge cookie files from all profile directories."""
    platform = system()
    
    if platform == "Windows":
        base_paths = [
            "~/AppData/Local/Microsoft/Edge/User Data",
        ]
    elif platform == "Darwin":  # macOS
        base_paths = [
            "~/Library/Application Support/Microsoft Edge",
        ]
    else:  # Linux
        base_paths = [
            "~/.config/microsoft-edge",
        ]
    
    cookie_files = []
    for base_path in base_paths:
        expanded_base = expanduser(base_path)
        if not exists(expanded_base):
            continue
        
        # Check Default profile first
        default_cookies = expanduser(f"{base_path}/Default/Cookies")
        if exists(default_cookies):
            cookie_files.append(default_cookies)
        
        # Check other profiles
        profile_pattern = expanduser(f"{base_path}/Profile */Cookies")
        cookie_files.extend(glob(profile_pattern))
        
        # Also check numbered profiles
        numbered_pattern = expanduser(f"{base_path}/Profile [0-9]*/Cookies")
        cookie_files.extend(glob(numbered_pattern))
    
    # Prioritize cookie files that contain LinkedIn cookies
    prioritized = []
    others = []
    
    for cookiefile in cookie_files:
        if has_linkedin_cookies(cookiefile, is_firefox=False):
            prioritized.append(cookiefile)
        else:
            others.append(cookiefile)
    
    return prioritized + others


def extract_cookies_from_firefox(cookiefile):
    """Extract LinkedIn cookies from Firefox cookie database."""
    try:
        conn = connect(f"file:{cookiefile}?immutable=1", uri=True)
        
        # Try multiple query strategies
        queries = [
            # Try baseDomain first (modern Firefox schema)
            "SELECT name, value, host, path, expiry, isSecure, isHttpOnly FROM moz_cookies WHERE (baseDomain='linkedin.com' OR baseDomain='.linkedin.com')",
            # Fallback to host-based query
            "SELECT name, value, host, path, expiry, isSecure, isHttpOnly FROM moz_cookies WHERE (host='linkedin.com' OR host='.linkedin.com' OR host='www.linkedin.com' OR host LIKE '%.linkedin.com')",
            # Try with any LinkedIn domain
            "SELECT name, value, host, path, expiry, isSecure, isHttpOnly FROM moz_cookies WHERE host LIKE '%linkedin.com'",
        ]
        
        for query in queries:
            try:
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                
                if rows:
                    cookies = []
                    for row in rows:
                        cookie = {
                            'name': row[0],
                            'value': row[1],
                            'domain': row[2] if row[2].startswith('.') else f".{row[2]}" if not row[2].startswith('.') and '.' in row[2] else row[2],
                            'path': row[3] or '/',
                            'expiry': row[4] if row[4] else None,
                            'secure': bool(row[5]) if row[5] is not None else True,
                            'httpOnly': bool(row[6]) if row[6] is not None else False,
                        }
                        cookies.append(cookie)
                    
                    conn.close()
                    return cookies
            except OperationalError:
                continue
        
        conn.close()
        
    except Exception as e:
        print(f"{YELLOW} Warning: Could not extract from Firefox {cookiefile}: {e}")
    return None


def extract_cookies_from_chrome_edge(cookiefile):
    """Extract LinkedIn cookies from Chrome/Edge cookie database."""
    try:
        # Try read-only access first
        conn = connect(f"file:{cookiefile}?immutable=1", uri=True)
        
        queries = [
            "SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly FROM cookies WHERE host_key LIKE '%linkedin.com'",
            "SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly FROM cookies WHERE host_key LIKE '%.linkedin.com'",
            "SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly FROM cookies WHERE host_key='www.linkedin.com'",
        ]
        
        for query in queries:
            try:
                cursor = conn.execute(query)
                rows = cursor.fetchall()
                
                if rows:
                    cookies = []
                    for row in rows:
                        host_key = row[2]
                        # Chrome/Edge uses host_key directly (no dot prefix needed)
                        domain = host_key if host_key.startswith('.') else f".{host_key}" if '.' in host_key else host_key
                        
                        # Handle encrypted values (Chrome/Edge may encrypt on Windows/macOS)
                        cookie_value = row[1]
                        if isinstance(cookie_value, bytes):
                            try:
                                cookie_value = cookie_value.decode('utf-8')
                            except UnicodeDecodeError:
                                # Value is encrypted, skip this cookie
                                continue
                        
                        cookie = {
                            'name': row[0],
                            'value': cookie_value,
                            'domain': domain,
                            'path': row[3] or '/',
                            'expiry': row[4] if row[4] else None,
                            'secure': bool(row[5]) if row[5] is not None else True,
                            'httpOnly': bool(row[6]) if row[6] is not None else False,
                        }
                        cookies.append(cookie)
                    
                    conn.close()
                    return cookies
            except OperationalError:
                continue
            except Exception:
                continue
        
        conn.close()
        
    except Exception as e:
        print(f"{YELLOW} Warning: Could not extract from Chrome/Edge {cookiefile}: {e}")
    return None


def extract_linkedin_cookies(browser=None, output_file='linkedin_cookies.json', quiet=False):
    """
    Extract LinkedIn cookies from browser cookie databases.
    
    Args:
        browser: Preferred browser ('firefox', 'chrome', 'edge') or None for auto-detect
        output_file: Output file path for cookies JSON
        quiet: Suppress non-error output
    
    Returns:
        Path to output file if successful, None otherwise
    """
    if not quiet:
        print(f"{CYAN} Extracting LinkedIn cookies from browser...")
    
    cookie_files = []
    browser_name = ""
    
    # Determine which browser to check
    if browser and browser.lower() == 'firefox':
        cookie_files = get_firefox_cookie_files()
        browser_name = "Firefox"
    elif browser and browser.lower() == 'chrome':
        cookie_files = get_chrome_cookie_files()
        browser_name = "Chrome"
    elif browser and browser.lower() == 'edge':
        cookie_files = get_edge_cookie_files()
        browser_name = "Edge"
    else:
        # Auto-detect: try all browsers in order
        if not quiet:
            print(f"{CYAN} Auto-detecting browser with LinkedIn cookies...")
        
        # Try Firefox first (often has LinkedIn logged in)
        firefox_files = get_firefox_cookie_files()
        if firefox_files:
            cookie_files = firefox_files
            browser_name = "Firefox"
        else:
            # Try Chrome
            chrome_files = get_chrome_cookie_files()
            if chrome_files:
                cookie_files = chrome_files
                browser_name = "Chrome"
            else:
                # Try Edge
                edge_files = get_edge_cookie_files()
                if edge_files:
                    cookie_files = edge_files
                    browser_name = "Edge"
    
    if not cookie_files:
        if not quiet:
            print(f"{RED} Error: No browser cookie files found")
            print(f"{YELLOW} Please make sure you are logged into LinkedIn in your browser")
        return None
    
    if not quiet:
        print(f"{CYAN} Checking {len(cookie_files)} cookie file(s) from {browser_name}...")
    
    # Try to extract cookies from each file until we find LinkedIn cookies
    all_cookies = []
    for cookiefile in cookie_files:
        if not quiet:
            print(f"{CYAN} Checking: {cookiefile}")
        
        cookies = None
        if 'firefox' in cookiefile.lower() or 'mozilla' in cookiefile.lower():
            cookies = extract_cookies_from_firefox(cookiefile)
        else:
            cookies = extract_cookies_from_chrome_edge(cookiefile)
        
        if cookies:
            all_cookies.extend(cookies)
            if not quiet:
                print(f"{GREEN} Found {len(cookies)} LinkedIn cookie(s)")
    
    if not all_cookies:
        if not quiet:
            print(f"{RED} Error: No LinkedIn cookies found")
            print(f"{YELLOW} Please make sure you are logged into LinkedIn in your browser")
        return None
    
    # Remove duplicates (keep first occurrence)
    seen = set()
    unique_cookies = []
    for cookie in all_cookies:
        key = (cookie['name'], cookie['domain'])
        if key not in seen:
            seen.add(key)
            unique_cookies.append(cookie)
    
    # Check if any authentication cookies were found
    auth_cookie_names = ['li_at', 'JSESSIONID', 'bcookie', 'bscookie']
    found_auth_cookies = any(c['name'] in auth_cookie_names for c in unique_cookies)
    
    if not found_auth_cookies:
        if not quiet:
            print(f"{YELLOW} Warning: No authentication cookies found (li_at, JSESSIONID, etc.)")
            print(f"{YELLOW} The extracted cookies may not be sufficient for authentication")
    
    # Save cookies to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unique_cookies, f, indent=2, ensure_ascii=False)
        
        if not quiet:
            print(f"{GREEN} Extracted {len(unique_cookies)} unique LinkedIn cookie(s)")
            print(f"{GREEN} Cookies saved to: {output_file}")
            if found_auth_cookies:
                print(f"{GREEN} Authentication cookies found - session should work")
        
        return output_file
    except Exception as e:
        if not quiet:
            print(f"{RED} Error saving cookies: {e}")
        return None


def main():
    parser = ArgumentParser(description="Extract LinkedIn cookies from browser")
    parser.add_argument('-b', '--browser', choices=['firefox', 'chrome', 'edge'],
                       help='Preferred browser (default: auto-detect)')
    parser.add_argument('-o', '--output', default='linkedin_cookies.json',
                       help='Output file path (default: linkedin_cookies.json)')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Suppress non-error output')
    
    args = parser.parse_args()
    
    result = extract_linkedin_cookies(
        browser=args.browser,
        output_file=args.output,
        quiet=args.quiet
    )
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

