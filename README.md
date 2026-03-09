# Cary ReqTrac API Client

A Python client for interacting with the Cary ReqTrac website (nccaryweb.myvscloud.com) to search for programs, manage wishlists, and handle shopping cart operations.

## ⚠️ Important: Cloudflare Protection

The Cary ReqTrac website uses **Cloudflare bot protection** that blocks standard HTTP requests. Two implementations are provided:

1. **`api_client.py`** - Standard `requests` library implementation
   - ❌ **Blocked by Cloudflare (403 Forbidden)**
   - Code structure is complete and production-ready
   - Will work if Cloudflare protection is bypassed

2. **`api_client_playwright.py`** - Playwright browser automation (RECOMMENDED)
   - ✅ **Bypasses Cloudflare by using real browser**
   - Uses Chrome browser via Playwright
   - More reliable but requires browser installation
   - Async/await syntax

**Recommendation**: Use the Playwright version (`api_client_playwright.py`) for actual usage.

## Overview

This client reverse-engineers the Cary ReqTrac web application API calls and provides a programmatic interface for:
- User authentication (login/logout)
- Searching for recreational programs
- Viewing program details
- Managing wishlists
- Adding items to shopping cart
- Viewing cart contents
- Accessing checkout

## APIs Discovered

### 1. Authentication System
- **Endpoint**: `POST /webtrac/web/login.html`
- **Method**: Two-step login process
  - Step 1: Submit username and password
  - Step 2: Resume session confirmation
- **Authentication**: Session-based with cookies (`_webtracsessionid`)
- **Security**: CSRF token required for all requests

### 2. Session Management
- **Endpoint**: `GET /webtrac/web/`
- **Purpose**: Initialize session and obtain CSRF token
- **Cookies Set**: `_webtracsessionid`, `_CookiesEnabled`, `_mobile`, `__cf_bm` (Cloudflare)

### 3. Program Search
- **Endpoint**: `GET /webtrac/web/search.html`
- **Parameters**:
  - `keyword`: Search term
  - `location`: Facility/location filter
  - `age`: Age filter
  - `beginmonth`: Month filter (1-12)
  - `page`: Page number (1-indexed, optional) - **NEW**
  - `search`: "yes" when paginating (required with page param) - **NEW**
  - `keywordoption`: Match type (e.g., "Match One")
  - `dayoption`: Day filter (default: "All")
  - `display`: View mode (default: "detail")
  - `module`: Module type (default: "AR" for Activities/Recreation)
- **Response**: HTML page with search results
- **Pagination**: Results are paginated at 25 per page, max 502 total

### 4. Item Information
- **Endpoint**: `GET /webtrac/web/iteminfo.html`
- **Parameters**:
  - `Module`: Module type (e.g., "AR")
  - `FMID`: Facility/item ID
- **Response**: HTML page with detailed program information

### 5. Wishlist Management
- **Endpoint**: `GET /webtrac/web/search.html?action=ProcessWishlist`
- **Parameters**:
  - `Module`: Module type
  - `FMID`: Item ID to add to wishlist
  - `action`: "ProcessWishlist"
- **Response**: Updated search page with wishlist status

### 6. Selection Update
- **Endpoint**: `GET /webtrac/web/search.html?Action=UpdateSelection`
- **Purpose**: Set date/time preferences before adding to cart
- **Parameters**:
  - `ARFMIDList`: Item ID(s)
  - `GlobalSalesArea_ARItemBeginDate`: Start date (MM/DD/YYYY)
  - `GlobalSalesArea_ARItemBeginTime`: Start time in seconds
  - `GlobalSalesArea_ARItemEndDate`: End date (MM/DD/YYYY)
  - `GlobalSalesArea_ARItemEndTime`: End time in seconds

### 7. Add to Cart
- **Endpoint**: `POST /webtrac/web/AddToCart.html`
- **Method**: Two-step process
  - Step 1: `GET /webtrac/web/search.html?action=ProcessAddToCart`
  - Step 2: `POST /webtrac/web/AddToCart.html` (multipart form)
- **Response**: 302 redirect to cart page on success

### 8. View Cart
- **Endpoint**: `GET /webtrac/web/cart.html`
- **Response**: HTML page with cart contents

### 9. Checkout
- **Endpoint**: `GET /webtrac/web/checkout.html`
- **Response**: HTML page with checkout form

## Authentication Details

The Cary ReqTrac system uses a combination of:

1. **Session Cookies**:
   - `_webtracsessionid`: Main session identifier
   - `_CookiesEnabled`: Cookie support flag
   - `_mobile`: Mobile detection flag
   - `__cf_bm`: Cloudflare bot management token

2. **CSRF Protection**:
   - Every request requires a `_csrf_token` parameter
   - Tokens are extracted from HTML responses (hidden form fields, URL parameters)
   - Tokens are dynamic and change with each response

3. **Two-Step Login**:
   - First request submits credentials
   - Second request confirms session resumption
   - Both require valid CSRF tokens

## Installation

### Option 1: Playwright Version (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Option 2: Requests Version (Blocked by Cloudflare)

```bash
pip install requests beautifulsoup4 lxml
```

### Dependencies

- **Core**: `requests`, `beautifulsoup4`, `lxml` - For HTTP requests and HTML parsing
- **Playwright** (recommended): `playwright` - For browser automation to bypass Cloudflare

## Usage

### Playwright Version (Recommended)

```python
import asyncio
from api_client_playwright import CaryReqTracClientPlaywright

async def main():
    # Use context manager for automatic cleanup
    async with CaryReqTracClientPlaywright(headless=False) as client:
        # Initialize session
        await client.initialize_session()

        # Login
        success = await client.login("your_username", "your_password")
        if not success:
            print("Login failed!")
            return

        # Search for programs
        success, html = await client.search_programs(
            keyword="TENNIS",
            age=12
        )

        if success:
            programs = client.parse_search_results(html)
            print(f"Found {len(programs)} programs")

        # Logout
        await client.logout()

# Run the async function
asyncio.run(main())
```

### Requests Version (Will be blocked by Cloudflare)

```python
from api_client import CaryReqTracClient

# Initialize client
client = CaryReqTracClient()

# Initialize session (gets cookies and CSRF token)
client.initialize_session()

# Login
success = client.login("your_username", "your_password")
if not success:
    print("Login failed!")
    exit(1)

# Search for programs
success, html = client.search_programs(
    keyword="LUNCH",
    location="Bond Park Boathouse",
    age=10,
    begin_month=6
)

if success:
    # Parse search results
    programs = client.parse_search_results(html)
    print(f"Found {len(programs)} programs")

    for program in programs:
        print(f"  - {program.get('name')} (ID: {program.get('fmid')})")

# Logout when done
client.logout()
```

### Advanced Example: Complete Workflow

```python
from api_client import CaryReqTracClient

client = CaryReqTracClient()
client.initialize_session()

# Login
if not client.login("username", "password"):
    exit(1)

# Search for programs
success, html = client.search_programs(keyword="TENNIS", age=12)

if success:
    programs = client.parse_search_results(html)

    if programs:
        # Get detailed info for first program
        item_id = programs[0].get('fmid')
        success, info = client.get_item_info(item_id)

        # Add to wishlist
        client.add_to_wishlist(item_id)

        # Update selection with dates/times
        client.update_selection(
            item_id=item_id,
            begin_date="07/13/2026",
            begin_time="43200",  # 12:00 PM in seconds
            end_date="07/17/2026",
            end_time="46800"     # 1:00 PM in seconds
        )

        # Add to cart
        if client.add_to_cart():
            # View cart
            success, cart_html = client.view_cart()
            print("Cart contents:", cart_html[:200])

            # Access checkout
            success, checkout_html = client.get_checkout_page()

client.logout()
```

### Search Parameters

The `search_programs` method accepts various filters:

```python
client.search_programs(
    keyword="SOCCER",           # Search term
    location="Community Center", # Facility filter
    age=8,                       # Age filter
    begin_month=7,               # July (1-12)
    keyword_option="Match One",  # "Match One" or "Match All"
    day_option="All",            # Day filter
    by_day_only="No",           # Show by day only
    show_with_available="No",   # Show only available slots
    display="detail",           # "detail" or "list"
    module="AR"                 # Module type
)
```

### Time Conversion Helper

Convert time to seconds for the API:

```python
def time_to_seconds(hours, minutes=0):
    """Convert hours and minutes to seconds since midnight."""
    return (hours * 3600) + (minutes * 60)

# Examples:
# 12:00 PM = time_to_seconds(12, 0) = 43200
# 1:00 PM = time_to_seconds(13, 0) = 46800
# 9:30 AM = time_to_seconds(9, 30) = 34200
```

### Pagination Support

The client supports automatic pagination for large result sets (25 results per page, max 502 total).

**Single Page (default behavior):**
```python
# Fetch only first page
success, html = client.search_programs(keyword="TENNIS", age=10)
results = client.parse_search_results(html)
# Returns: ~25 results (first page only)
```

**Specific Page:**
```python
# Fetch page 2
success, html = client.search_programs(keyword="TENNIS", age=10, page=2)
results = client.parse_search_results(html)
# Returns: ~25 results from page 2 (results 26-50)
```

**All Pages (recommended for complete results):**
```python
# Automatically fetch all pages
success, all_results, total_count = client.search_programs_paginated(
    keyword="TENNIS",
    age=10
)
print(f"Found {len(all_results)} results out of {total_count} total")
# Returns: All results across all pages (may be 500+)
```

**With Result Limit (default: unlimited):**
```python
# Stop after 50 results (fetches ~2 pages)
success, results, total_count = client.search_programs_paginated(
    keyword="TENNIS",
    age=10,
    max_results=50
)
print(f"Limited to {len(results)} of {total_count} total")
# Returns: First 50 results (stops early for performance)
```

**Check Pagination Metadata:**
```python
success, html = client.search_programs(keyword="TENNIS", age=10)
metadata = client.parse_pagination_metadata(html)

if metadata:
    print(f"Showing results {metadata['showing_start']}-{metadata['showing_end']}")
    print(f"Total results: {metadata['total']}")
    print(f"Total pages: {metadata['total_pages']}")
else:
    print("Single page of results (no pagination)")
```

**Generic Pagination (for other endpoints):**
```python
# Can be used for cart, wishlist, or any paginated endpoint
def fetch_cart_page(page: int):
    # Add pagination param to cart view (hypothetical)
    return client.view_cart(page=page)

success, all_items, total = client._fetch_all_pages(
    fetch_page_func=fetch_cart_page,
    parse_func=client.parse_cart_results,  # hypothetical
    max_results=100
)
```

## API Client Methods

### Session Management

- `initialize_session()` → `bool`
  - Initializes session and obtains CSRF token
  - Should be called before login

- `login(username: str, password: str)` → `bool`
  - Authenticates user with two-step login process
  - Returns True on success

- `logout()` → `bool`
  - Logs out and clears session

### Program Search & Information

- `search_programs(keyword, location, age, begin_month, page=None, ...)` → `(bool, Optional[str])`
  - Searches for programs with various filters (single page)
  - **New:** `page` parameter to fetch specific page (1-indexed)
  - Returns tuple of (success, html_content)

- `search_programs_paginated(keyword, location, age, begin_month, max_results=None, ...)` → `(bool, List[Dict], int)`
  - **NEW:** Searches for programs and automatically fetches all pages
  - Uses generic pagination helper
  - Returns tuple of (success, all_results, total_count)
  - `max_results`: Optional limit to stop fetching early (default: None for unlimited)

- `parse_pagination_metadata(html: str)` → `Optional[Dict[str, int]]`
  - **NEW:** Extracts pagination metadata from HTML responses
  - Returns dict with: `showing_start`, `showing_end`, `total`, `total_pages`
  - Works for any paginated endpoint (search, cart, wishlist)

- `_fetch_all_pages(fetch_func, parse_func, max_results=None)` → `(bool, List[Dict], int)`
  - **NEW:** Generic pagination helper for any endpoint
  - Takes fetch and parse functions as arguments
  - Can be reused for cart, wishlist, or other paginated endpoints

- `get_item_info(item_id: str, module: str)` → `(bool, Optional[str])`
  - Gets detailed information about a specific program
  - Returns tuple of (success, html_content)

- `parse_search_results(html: str)` → `List[Dict]`
  - Parses HTML search results into structured data
  - Returns list of program dictionaries

### Wishlist & Cart

- `add_to_wishlist(item_id: str, module: str)` → `bool`
  - Adds item to wishlist
  - Returns True on success

- `update_selection(item_id, begin_date, begin_time, end_date, end_time, ...)` → `bool`
  - Updates item selection with date/time preferences
  - Required before adding to cart

- `add_to_cart()` → `bool`
  - Adds selected items to shopping cart
  - Returns True on success

- `view_cart()` → `(bool, Optional[str])`
  - Views cart contents
  - Returns tuple of (success, html_content)

- `get_checkout_page()` → `(bool, Optional[str])`
  - Accesses checkout page
  - Returns tuple of (success, html_content)

## Limitations & Caveats

### 1. HTML Responses
- The API returns HTML, not JSON
- Data extraction requires parsing HTML with BeautifulSoup
- Site structure changes may break the parser

### 2. CSRF Token Management
- CSRF tokens must be extracted from each response
- Tokens are dynamic and session-specific
- Failed token extraction will cause subsequent requests to fail

### 3. Cloudflare Protection
- Site uses Cloudflare bot protection (`__cf_bm` cookie)
- May block requests if they appear automated
- Use realistic User-Agent headers (already configured)

### 4. Session Expiration
- Sessions may expire after inactivity
- No automatic session renewal implemented
- May need to re-login if session expires

### 5. Incomplete Checkout
- This client does not complete payment transactions
- Checkout page access is provided but payment is not automated
- Manual completion may be required

### 6. Rate Limiting
- Unknown rate limits may exist
- Implement delays between requests if needed

### 7. Multi-Part Forms
- Some POST requests use multipart form data
- Form data appears to be managed by JavaScript
- Empty form submissions work but may be fragile

## Error Handling

The client includes comprehensive error handling:

```python
try:
    success, html = client.search_programs(keyword="TEST")
    if not success:
        print("Search failed")
except Exception as e:
    print(f"Error occurred: {e}")
```

All methods return boolean success indicators or tuples with success flags.

## Logging

The client uses Python's `logging` module:

```python
import logging

# Set log level
logging.basicConfig(level=logging.DEBUG)

# Create client
client = CaryReqTracClient()
```

Log levels:
- `DEBUG`: Detailed request/response information
- `INFO`: General operation status
- `WARNING`: Non-critical issues
- `ERROR`: Operation failures

## Security Considerations

1. **Credential Storage**: Never hardcode credentials in scripts
   ```python
   import os
   username = os.getenv('REQTRAC_USERNAME')
   password = os.getenv('REQTRAC_PASSWORD')
   ```

2. **HTTPS**: All requests use HTTPS by default

3. **Session Management**: Sessions are isolated per client instance

4. **Token Security**: CSRF tokens are handled automatically

## Troubleshooting

### Login Fails
- Verify credentials are correct
- Check if CSRF token was extracted successfully
- Ensure session was initialized before login

### CSRF Token Not Found
- The site structure may have changed
- Check HTML response for token location
- Update `_extract_csrf_token()` method

### Cloudflare Blocking
- Add delays between requests
- Use residential IP or proxy
- Consider switching to Playwright with real browser

### Search Returns No Results
- Verify search parameters are valid
- Check if authentication is still active
- Review HTML response for error messages

## Development & Testing

Run the included example:

```bash
python api_client.py
```

Note: Update the credentials in the `main()` function before running.

## Future Enhancements

Potential improvements:
- Add payment processing (if needed)
- Implement session auto-renewal
- Add more robust HTML parsing
- Create async version for concurrent requests
- Add retry logic with exponential backoff
- Implement response caching
- Add webhook/notification support

## License

This is a reverse-engineered client for educational purposes. Use responsibly and in accordance with the Cary ReqTrac website's terms of service.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the HAR file for actual API behavior
3. Inspect HTML responses for structural changes
4. Enable DEBUG logging for detailed information

## Version History

- **v1.1.0** (2026-03-08): Pagination support
  - Added automatic pagination for search results
  - New `search_programs_paginated()` method for fetching all pages
  - New `parse_pagination_metadata()` for extracting pagination info
  - Generic `_fetch_all_pages()` helper for reusable pagination
  - CLI default limit of 50 results for better performance
  - Support for `--limit` and `--page` options in CLI

- **v1.0.0** (2026-03-07): Initial release
  - Basic authentication
  - Program search
  - Wishlist management
  - Cart operations
  - Checkout access
