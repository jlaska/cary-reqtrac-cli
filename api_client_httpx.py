"""
Cary ReqTrac API Client (httpx version)

This module uses httpx instead of requests to bypass Cloudflare bot protection.
httpx's different TLS fingerprint allows it to pass Cloudflare checks.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple, Callable
from urllib.parse import urljoin, parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup


# Get logger (do not configure here - let CLI handle it)
logger = logging.getLogger(__name__)


class CaryReqTracClientHttpx:
    """Client for interacting with the Cary ReqTrac website using httpx."""

    BASE_URL = "https://nccaryweb.myvscloud.com"

    def __init__(self):
        """Initialize the ReqTrac client with httpx."""
        self.client = httpx.Client(
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            },
            follow_redirects=True,
            timeout=30.0
        )
        self.csrf_token: Optional[str] = None
        self.is_authenticated = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the httpx client."""
        self.client.close()

    def _extract_csrf_token(self, html: str) -> Optional[str]:
        """
        Extract CSRF token from HTML response.

        Args:
            html: HTML content to parse

        Returns:
            CSRF token if found, None otherwise
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Look for CSRF token in hidden input fields
            csrf_input = soup.find('input', {'name': '_csrf_token'})
            if csrf_input and csrf_input.get('value'):
                return csrf_input['value']

            # Look for CSRF token in links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if '_csrf_token=' in href:
                    match = re.search(r'_csrf_token=([^&]+)', href)
                    if match:
                        return match.group(1)

            # Look for CSRF token in script tags or meta tags
            meta_csrf = soup.find('meta', {'name': 'csrf-token'})
            if meta_csrf and meta_csrf.get('content'):
                return meta_csrf['content']

            logger.warning("CSRF token not found in HTML")
            return None

        except Exception as e:
            logger.error(f"Error extracting CSRF token: {e}")
            return None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Any] = None,  # Can be Dict or List of tuples
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with automatic CSRF token injection.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters (dict or list of tuples for multi-value params)
            data: Request body data
            **kwargs: Additional arguments for httpx

        Returns:
            Response object
        """
        url = urljoin(self.BASE_URL, endpoint)

        # Add CSRF token to params if available
        if self.csrf_token:
            if params is None:
                params = {}

            # Handle both dict and list of tuples
            if isinstance(params, dict):
                if '_csrf_token' not in params:
                    params['_csrf_token'] = self.csrf_token
            elif isinstance(params, list):
                # Check if CSRF token already in list
                has_csrf = any(k == '_csrf_token' for k, v in params)
                if not has_csrf:
                    params.append(('_csrf_token', self.csrf_token))

        logger.debug(f"{method} {url}")

        try:
            response = self.client.request(
                method,
                url,
                params=params,
                data=data,
                **kwargs
            )
            response.raise_for_status()

            # Try to extract new CSRF token from response
            if 'text/html' in response.headers.get('content-type', ''):
                new_token = self._extract_csrf_token(response.text)
                if new_token:
                    self.csrf_token = new_token
                    logger.debug(f"Updated CSRF token: {self.csrf_token[:20]}...")

            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"Request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Request error: {e}")
            raise

    def initialize_session(self) -> bool:
        """
        Initialize a session by visiting the homepage to get cookies and CSRF token.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Initializing session...")
            response = self._make_request('GET', '/webtrac/web/')

            # Extract CSRF token
            self.csrf_token = self._extract_csrf_token(response.text)

            if self.csrf_token:
                logger.info("Session initialized successfully")
                return True
            else:
                logger.warning("Session initialized but no CSRF token found")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            return False

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate with the ReqTrac system.

        This is a two-step process:
        1. Submit credentials
        2. Resume session

        Args:
            username: User's username
            password: User's password

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Step 0: Initialize session if needed
            if not self.csrf_token:
                self.initialize_session()

            # Step 1: Get login page to ensure we have CSRF token
            logger.info("Getting login page...")
            login_page = self._make_request('GET', '/webtrac/web/login')

            # Step 2: Submit login credentials
            logger.info(f"Logging in as {username}...")
            login_data = {
                'Action': 'process',
                'SubAction': '',
                '_csrf_token': self.csrf_token,
                'weblogin_username': username,
                'weblogin_password': password,
                'weblogin_buttonlogin': 'yes'
            }

            response = self._make_request(
                'POST',
                '/webtrac/web/login.html',
                data=login_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            # Step 3: Resume session (second login step)
            logger.info("Resuming session...")
            resume_data = {
                'Action': 'process',
                'SubAction': '',
                '_csrf_token': self.csrf_token,
                'loginresumesession_continue': 'yes'
            }

            response = self._make_request(
                'POST',
                '/webtrac/web/login.html',
                data=resume_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            # Check if login was successful by looking for indicators in the response
            if 'logout' in response.text.lower() or 'my account' in response.text.lower():
                logger.info("Login successful")
                self.is_authenticated = True
                return True
            else:
                logger.error("Login failed - no logout link found")
                return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def search_programs(
        self,
        keyword: Optional[str] = None,
        locations: Optional[List[str]] = None,
        instructors: Optional[List[str]] = None,
        age: Optional[int] = None,
        begin_month: Optional[int] = None,
        page: Optional[int] = None,
        keyword_option: str = "Match One",
        day_option: str = "All",
        by_day_only: str = "No",
        show_with_available: str = "No",
        display: str = "detail",
        module: str = "AR"
    ) -> Tuple[bool, Optional[str]]:
        """
        Search for programs with various filters (single page).

        Args:
            keyword: Search keyword
            locations: List of location filters (supports multiple)
            instructors: List of instructor filters (supports multiple)
            age: Age filter
            begin_month: Beginning month (1-12)
            page: Page number (1-indexed, None for first page without pagination param)
            keyword_option: Keyword matching option (default: "Match One")
            day_option: Day filter option (default: "All")
            by_day_only: Show by day only (default: "No")
            show_with_available: Show only available (default: "No")
            display: Display mode (default: "detail")
            module: Module type (default: "AR")

        Returns:
            Tuple of (success: bool, html_content: Optional[str])
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return False, None

            logger.info(f"Searching programs with keyword: {keyword}")

            # Build search parameters - include ALL form fields as the server expects
            # Even empty fields must be present for the search to work correctly
            params = {
                'Action': 'Start',
                'SubAction': '',
                'keyword': keyword or '',
                'keywordoption': keyword_option,
                'primarycode': '',
                'type': '',
                'age': str(age) if age is not None else '',
                'endmonth': '',
                'category': '',
                'grade': '',
                'beginmonth': str(begin_month) if begin_month is not None else '',
                'registrationevent': '',
                'dayoption': day_option,
                'timeblock': '',
                'gender': '',
                'spotsavailable': '',
                'bydayonly': by_day_only,
                'beginyear': '',
                'season': '',
                'showwithavailable': show_with_available,
                'display': display,
                'module': module,
                'multiselectlist_value': '',
                'arwebsearch_noresultsbutton': 'yes'
            }

            # Add page parameter if specified
            if page is not None:
                params['page'] = str(page)
                params['search'] = 'yes'

            # Add locations and/or instructors if specified (supports multiple values)
            # Note: httpx will automatically encode multiple values with same key as location=A&location=B
            if locations or instructors:
                # For httpx, we need to pass a list of tuples for multiple values
                # Build params as list of tuples to support multiple locations/instructors
                params_list = [(k, v) for k, v in params.items()]

                if locations:
                    for loc in locations:
                        params_list.append(('location', loc))

                if instructors:
                    for inst in instructors:
                        params_list.append(('instructor', inst))

                response = self._make_request('GET', '/webtrac/web/search.html', params=params_list)
            else:
                response = self._make_request('GET', '/webtrac/web/search.html', params=params)

            logger.info("Search completed successfully")
            return True, response.text

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return False, None

    def get_item_info(self, item_id: str, module: str = "AR") -> Tuple[bool, Optional[str]]:
        """
        Get detailed information about a specific program/item.

        Args:
            item_id: The FMID (item ID) to retrieve
            module: Module type (default: "AR")

        Returns:
            Tuple of (success: bool, html_content: Optional[str])
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return False, None

            logger.info(f"Getting info for item: {item_id}")

            params = {
                'Module': module,
                'FMID': item_id
            }

            response = self._make_request('GET', '/webtrac/web/iteminfo.html', params=params)

            logger.info("Item info retrieved successfully")
            return True, response.text

        except Exception as e:
            logger.error(f"Failed to get item info: {e}")
            return False, None

    def add_to_wishlist(self, item_id: str, module: str = "AR") -> bool:
        """
        Add an item to the wishlist.

        Args:
            item_id: The FMID (item ID) to add to wishlist
            module: Module type (default: "AR")

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return False

            logger.info(f"Adding item {item_id} to wishlist...")

            params = {
                'Module': module,
                'FMID': item_id,
                'action': 'ProcessWishlist',
                '_': ''  # Timestamp parameter, can be empty
            }

            response = self._make_request('GET', '/webtrac/web/search.html', params=params)

            logger.info("Item added to wishlist successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to add to wishlist: {e}")
            return False

    def update_selection(
        self,
        item_id: str,
        begin_date: str,
        begin_time: str,
        end_date: str,
        end_time: str,
        module: str = "AR",
        from_program: str = "search"
    ) -> bool:
        """
        Update item selection with date/time parameters before adding to cart.

        Args:
            item_id: The FMID (item ID)
            begin_date: Begin date (format: MM/DD/YYYY)
            begin_time: Begin time in seconds (e.g., "43200" for 12:00 PM)
            end_date: End date (format: MM/DD/YYYY)
            end_time: End time in seconds
            module: Module type (default: "AR")
            from_program: Source program (default: "search")

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return False

            logger.info(f"Updating selection for item {item_id}...")

            params = {
                'Action': 'UpdateSelection',
                'Module': module,
                'ARFMIDList': item_id,
                'FromProgram': from_program,
                'GlobalSalesArea_ARItemBeginDate': begin_date,
                'GlobalSalesArea_ARItemBeginTime': begin_time,
                'GlobalSalesArea_ARItemEndDate': end_date,
                'GlobalSalesArea_ARItemEndTime': end_time,
                '_': ''  # Timestamp parameter
            }

            response = self._make_request('GET', '/webtrac/web/search.html', params=params)

            logger.info("Selection updated successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to update selection: {e}")
            return False

    def add_to_cart(self) -> bool:
        """
        Add selected items to the shopping cart.

        This is a two-step process:
        1. Initiate the add to cart action
        2. Submit the multipart form

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return False

            logger.info("Adding items to cart...")

            # Step 1: Initiate add to cart
            params = {'action': 'ProcessAddToCart'}
            response = self._make_request('GET', '/webtrac/web/search.html', params=params)

            # Step 2: Submit the add to cart form (multipart)
            response = self._make_request(
                'POST',
                '/webtrac/web/AddToCart.html',
                data={}
            )

            # Check if successful
            if 'cart.html' in str(response.url) or response.status_code == 302:
                logger.info("Items added to cart successfully")
                return True
            else:
                logger.warning("Add to cart completed but no redirect to cart detected")
                return True

        except Exception as e:
            logger.error(f"Failed to add to cart: {e}")
            return False

    def view_cart(self) -> Tuple[bool, Optional[str]]:
        """
        View the shopping cart contents.

        Returns:
            Tuple of (success: bool, html_content: Optional[str])
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return False, None

            logger.info("Viewing cart...")

            response = self._make_request('GET', '/webtrac/web/cart.html')

            logger.info("Cart retrieved successfully")
            return True, response.text

        except Exception as e:
            logger.error(f"Failed to view cart: {e}")
            return False, None

    def get_checkout_page(self) -> Tuple[bool, Optional[str]]:
        """
        Access the checkout page.

        Returns:
            Tuple of (success: bool, html_content: Optional[str])
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return False, None

            logger.info("Accessing checkout page...")

            response = self._make_request('GET', '/webtrac/web/checkout.html')

            logger.info("Checkout page retrieved successfully")
            return True, response.text

        except Exception as e:
            logger.error(f"Failed to access checkout: {e}")
            return False, None

    def parse_search_results(self, html: str) -> List[Dict[str, str]]:
        """
        Parse search results HTML to extract program information.

        Args:
            html: HTML content from search results

        Returns:
            List of dictionaries containing program details
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            results = []

            # Look for all links that contain FMID (program links)
            program_links = soup.find_all('a', href=re.compile(r'FMID=\d+'))

            seen_fmids = set()
            for link in program_links:
                # Extract FMID from link
                match = re.search(r'FMID=(\d+)', link['href'])
                if not match:
                    continue

                fmid = match.group(1)

                # Skip duplicates (same program appears multiple times)
                if fmid in seen_fmids:
                    continue
                seen_fmids.add(fmid)

                program_info = {
                    'fmid': fmid,
                    'name': link.get_text(strip=True)
                }

                # Try to find the row containing this link for more details
                row = link.find_parent('tr')
                if row:
                    cells = row.find_all('td')
                    if cells:
                        # Extract text from all cells
                        cell_texts = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
                        program_info['details'] = cell_texts

                        # Try to extract specific information
                        for cell in cells:
                            title = cell.get('data-title', '')
                            text = cell.get_text(strip=True)

                            if title == 'Activity #':
                                program_info['activity_number'] = text
                            elif title == 'Description':
                                program_info['description'] = text
                            elif title == 'Dates':
                                program_info['dates'] = text
                            elif title == 'Location':
                                program_info['location'] = text
                            elif title == 'Fee' or title == 'Fees':
                                program_info['fee'] = text
                            elif title == 'Age':
                                program_info['age'] = text
                            elif title == 'Time':
                                program_info['time'] = text
                            elif title == 'Status':
                                program_info['status'] = text

                results.append(program_info)

            logger.info(f"Parsed {len(results)} programs from search results")
            return results

        except Exception as e:
            logger.error(f"Failed to parse search results: {e}")
            return []

    def parse_pagination_metadata(self, html: str) -> Optional[Dict[str, int]]:
        """
        Extract pagination metadata from any paginated response.

        Works for: search results, cart view, wishlist, etc.

        Args:
            html: HTML content to parse

        Returns:
            Dict with: showing_start, showing_end, total, total_pages
            None if no pagination found
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            header_subtext = soup.find('span', class_='header__subtext')

            if header_subtext:
                text = header_subtext.get_text()
                match = re.match(r'Showing results (\d+)-(\d+) of (\d+)', text)
                if match:
                    showing_start = int(match.group(1))
                    showing_end = int(match.group(2))
                    total = int(match.group(3))
                    return {
                        'showing_start': showing_start,
                        'showing_end': showing_end,
                        'total': total,
                        'total_pages': (total + 24) // 25  # 25 results per page
                    }

            return None

        except Exception as e:
            logger.warning(f"Failed to parse pagination metadata: {e}")
            return None

    def _fetch_all_pages(
        self,
        fetch_page_func: Callable[[int], Tuple[bool, str]],
        parse_func: Callable[[str], List[Dict]],
        max_results: Optional[int] = None
    ) -> Tuple[bool, List[Dict], int]:
        """
        Generic pagination helper - fetches all pages for any endpoint.

        Args:
            fetch_page_func: Function that takes page number, returns (success, html)
            parse_func: Function that takes html, returns list of parsed items
            max_results: Stop when this many results collected

        Returns:
            Tuple of (success, all_results, total_count)

        Can be used for search, cart, wishlist, or any paginated endpoint.
        """
        all_results = []

        # Fetch first page
        success, html = fetch_page_func(1)
        if not success:
            return False, [], 0

        results = parse_func(html)
        all_results.extend(results)

        # Check for pagination
        metadata = self.parse_pagination_metadata(html)
        if not metadata:
            # No pagination info, single page of results
            return True, all_results, len(all_results)

        total_count = metadata['total']
        total_pages = metadata['total_pages']

        # Log pagination info
        logger.info(f"Found {total_count} total results across {total_pages} pages")

        # Check if already done
        if max_results and len(all_results) >= max_results:
            return True, all_results[:max_results], total_count

        # Fetch remaining pages
        for page_num in range(2, total_pages + 1):
            logger.info(f"Fetching page {page_num}/{total_pages}...")

            success, html = fetch_page_func(page_num)
            if not success:
                logger.warning(f"Failed to fetch page {page_num}")
                break

            results = parse_func(html)
            all_results.extend(results)

            if max_results and len(all_results) >= max_results:
                logger.info(f"Reached limit of {max_results} results")
                break

        return True, all_results, total_count

    def search_programs_paginated(
        self,
        keyword: Optional[str] = None,
        locations: Optional[List[str]] = None,
        instructors: Optional[List[str]] = None,
        age: Optional[int] = None,
        begin_month: Optional[int] = None,
        max_results: Optional[int] = None
    ) -> Tuple[bool, List[Dict[str, str]], int]:
        """
        Search for programs, automatically fetching all pages.

        Uses generic _fetch_all_pages() helper.

        Args:
            keyword: Search keyword
            locations: List of location filters
            instructors: List of instructor filters
            age: Age filter
            begin_month: Beginning month (1-12)
            max_results: Stop fetching once we have this many results

        Returns:
            Tuple of (success, all_results, total_count)
        """
        # Define page fetcher for this specific endpoint
        def fetch_page(page: int) -> Tuple[bool, str]:
            return self.search_programs(
                keyword=keyword,
                locations=locations,
                instructors=instructors,
                age=age,
                begin_month=begin_month,
                page=page
            )

        # Use generic pagination helper
        return self._fetch_all_pages(
            fetch_page_func=fetch_page,
            parse_func=self.parse_search_results,
            max_results=max_results
        )

    def get_locations(self) -> List[str]:
        """
        Get list of available locations from search page.

        Returns:
            List of location names
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return []

            logger.info("Fetching available locations...")

            # Get search page
            response = self._make_request('GET', '/webtrac/web/search.html', params={'module': 'AR'})

            # Parse locations from select dropdown
            soup = BeautifulSoup(response.text, 'html.parser')
            location_select = soup.find('select', {'name': 'location'})

            if not location_select:
                logger.warning("Location dropdown not found")
                return []

            locations = []
            for option in location_select.find_all('option'):
                value = option.get('value', '').strip()
                if value and value != 'Multiple Locations':
                    locations.append(value)

            logger.info(f"Found {len(locations)} locations")
            return sorted(locations)

        except Exception as e:
            logger.error(f"Failed to get locations: {e}")
            return []

    def get_instructors(self) -> List[Dict[str, str]]:
        """
        Get list of available instructors from search page.

        Returns:
            List of dicts with 'value' (ID) and 'name' (display name)
        """
        try:
            if not self.is_authenticated:
                logger.error("Not authenticated. Please login first.")
                return []

            logger.info("Fetching available instructors...")

            # Get search page
            response = self._make_request('GET', '/webtrac/web/search.html', params={'module': 'AR'})

            # Parse instructors from select dropdown
            soup = BeautifulSoup(response.text, 'html.parser')
            instructor_select = soup.find('select', {'name': 'instructor'})

            if not instructor_select:
                logger.warning("Instructor dropdown not found")
                return []

            instructors = []
            for option in instructor_select.find_all('option'):
                value = option.get('value', '').strip()
                name = option.get_text(strip=True)
                if value and name:
                    instructors.append({
                        'value': value,
                        'name': name
                    })

            logger.info(f"Found {len(instructors)} instructors")
            return instructors

        except Exception as e:
            logger.error(f"Failed to get instructors: {e}")
            return []

    def logout(self) -> bool:
        """
        Logout from the system.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Logging out...")

            response = self._make_request(
                'GET',
                '/webtrac/web/logout.html'
            )

            self.is_authenticated = False
            self.csrf_token = None

            logger.info("Logged out successfully")
            return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    @property
    def cookies(self):
        """Get cookies as a dict (for session persistence)."""
        return dict(self.client.cookies)

    def set_cookies(self, cookies: Dict[str, str]):
        """Set cookies from a dict (for session restore)."""
        for name, value in cookies.items():
            self.client.cookies.set(name, value)
