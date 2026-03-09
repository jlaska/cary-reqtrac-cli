# Cary ReqTrac CLI

kubectl-style CLI for interacting with the Cary ReqTrac recreation program registration system.

## Installation

**Prerequisites:** Install [uv](https://docs.astral.sh/uv/) for Python dependency management:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**No other installation needed!** The `reqtrac` wrapper script uses `uv` to automatically manage all dependencies.

## Quick Start

### 1. Login
```bash
# Interactive login (prompts for credentials)
./reqtrac auth login

# Login with credentials from environment variables
export REQTRAC_USERNAME=your_username
export REQTRAC_PASSWORD=your_password
./reqtrac auth login

# Login with command line options
./reqtrac auth login -u your_username -p your_password
```

### 2. Search for Programs
```bash
# Search by keyword
./reqtrac programs search --keyword TENNIS

# Search with multiple filters
./reqtrac programs search --keyword LUNCH --age 10 --month 6

# Get JSON output
./reqtrac programs search --keyword SWIM -o json

# Get details for specific program
./reqtrac programs get 12345
```

### 3. Add to Wishlist
```bash
./reqtrac wishlist add 12345
```

### 4. Add to Cart
```bash
./reqtrac cart add 12345 \
  --begin-date "07/13/2026" \
  --begin-time "43200" \
  --end-date "07/17/2026" \
  --end-time "46800"
```

### 5. View Cart and Checkout
```bash
# View cart contents
./reqtrac cart view

# Access checkout page
./reqtrac cart checkout
```

### 6. Logout
```bash
./reqtrac auth logout
```

## Command Reference

### Global Options
- `--verbose, -v` - Enable debug logging
- `--output, -o` - Output format: `table`, `json`, `raw` (default: `table`)
- `--config, -c` - Config file path (default: `~/.config/reqtrac/config.json`)

### Authentication Commands

#### `auth login`
Login and save session.

**Options:**
- `--username, -u` - Username (or set `REQTRAC_USERNAME`)
- `--password, -p` - Password (or set `REQTRAC_PASSWORD`)

**Credential Priority:**
1. Command line options
2. Environment variables (`REQTRAC_USERNAME`, `REQTRAC_PASSWORD`)
3. Config file (`~/.config/reqtrac/config.json`)
4. Interactive prompt

#### `auth logout`
Logout and clear session.

#### `auth status`
Show current authentication status.

### Program Commands

#### `programs search`
Search for programs with filters.

**Pagination Behavior:**
- **Default**: Returns up to 50 results (fetches pages until limit reached)
- Use `--limit 0` for unlimited results (fetches all pages)
- Use `--limit N` to change the result limit
- Use `--page N` to fetch only a specific page (overrides `--limit`)

**Options:**
- `--keyword, -k` - Search keyword
- `--location, -l` - Location filter (supports glob patterns: *, ?, [])
- `--instructor, -i` - Instructor ID filter (supports glob patterns)
- `--age, -a` - Age filter (integer)
- `--month, -m` - Beginning month (1-12)
- `--page, -p` - Fetch specific page only (overrides --limit)
- `--limit` - Limit total results returned (default: 50, use 0 for unlimited)
- `--display, -d` - Display mode: `detail`, `calendar` (default: `detail`)

**Basic Examples:**
```bash
./reqtrac programs search --keyword TENNIS
./reqtrac programs search -k LUNCH -l "Bond Park" -a 10 -m 6
./reqtrac programs search -k SWIM -o json
./reqtrac programs search -l "Bond*" --age 10  # Glob pattern
./reqtrac programs search -i "*Williams*" -k TENNIS  # Multiple filters
```

**Pagination Examples:**
```bash
# Default: first 50 results (fast)
./reqtrac programs search --age 10

# Get all results (may be slow for large searches)
./reqtrac programs search --age 10 --limit 0

# Get first 100 results
./reqtrac programs search --age 10 --limit 100

# Fetch only first page (25 results max)
./reqtrac programs search --age 10 --page 1

# Fetch specific page
./reqtrac programs search --age 10 --page 2

# Combine filters with pagination
./reqtrac programs search -l "Bond*" -a 10 --limit 100

# See pagination progress in verbose mode
./reqtrac -v programs search --age 10 --limit 0
```

#### `programs get <program_id>`
Get details for a specific program ID.

**Arguments:**
- `program_id` - The program FMID to retrieve

**Examples:**
```bash
./reqtrac programs get 12345
./reqtrac programs get 12345 -o json
```

### Wishlist Commands

#### `wishlist add <program_id>`
Add a program to wishlist.

**Arguments:**
- `program_id` - The program FMID to add

**Examples:**
```bash
./reqtrac wishlist add 12345
```

#### `wishlist list`
List wishlist items (not yet implemented).

### Cart Commands

#### `cart add <program_id>`
Add program to cart with date/time selection.

**Arguments:**
- `program_id` - The program FMID to add

**Options:**
- `--begin-date` - Begin date (MM/DD/YYYY) **[required]**
- `--begin-time` - Begin time in seconds (e.g., `43200` for 12:00 PM) **[required]**
- `--end-date` - End date (MM/DD/YYYY) **[required]**
- `--end-time` - End time in seconds **[required]**

**Time Conversion:**
- Midnight (12:00 AM) = 0
- 6:00 AM = 21600
- 12:00 PM (noon) = 43200
- 6:00 PM = 64800

**Examples:**
```bash
./reqtrac cart add 12345 \
  --begin-date "07/13/2026" \
  --begin-time "43200" \
  --end-date "07/17/2026" \
  --end-time "46800"
```

#### `cart view`
View current cart contents.

**Examples:**
```bash
./reqtrac cart view
./reqtrac cart view -o json
```

#### `cart checkout`
Access checkout page.

**Examples:**
```bash
./reqtrac cart checkout
```

### Configuration Commands

#### `config set <key> <value>`
Set a configuration value.

**Arguments:**
- `key` - Configuration key (`username`, `password`, `base_url`)
- `value` - Configuration value

**Examples:**
```bash
./reqtrac config set username myuser
./reqtrac config set password mypassword
./reqtrac config set base_url https://custom.url.com
```

#### `config show`
Show current configuration (passwords are masked).

**Examples:**
```bash
./reqtrac config show
```

## Pagination

Search results in Cary ReqTrac are paginated (25 results per page, max 502 total). The CLI handles pagination automatically with sensible defaults.

### Default Behavior
By default, searches return up to **50 results** (fetches 2 pages). This provides a good balance between speed and completeness.

**Example:**
```bash
# Returns first 50 programs (fetches 2 pages)
./reqtrac programs search --age 10
```

### Getting All Results

For complete results, use `--limit 0`:
```bash
# Returns ALL matching programs (fetches all pages)
./reqtrac programs search --age 10 --limit 0
# Note: For 500+ results, this may take 10-20 seconds
```

### Custom Limits

Adjust the limit to your needs:
```bash
# Get first 100 results
./reqtrac programs search --age 10 --limit 100

# Get first 10 results
./reqtrac programs search --age 10 --limit 10
```

### Specific Pages

Fetch a single page directly (fastest option):
```bash
# Fetch only first page (25 results max)
./reqtrac programs search --age 10 --page 1

# Fetch page 2 (results 26-50)
./reqtrac programs search --age 10 --page 2

# Note: --page overrides --limit
```

### Progress Tracking

Use verbose mode to see pagination progress:
```bash
./reqtrac -v programs search --age 10 --limit 0
# Output:
# INFO - Found 502 total results across 21 pages
# INFO - Fetching page 2/21...
# INFO - Fetching page 3/21...
# ...
```

### Result Indicators

When results are limited, the CLI shows a count:
```bash
$ ./reqtrac programs search --age 10
# Showing 50 of 502 total results (limited to 50)
ID          ACTIVITY        NAME                 ...
...
```

### Performance Comparison

| Command | Results | Pages Fetched | Approx. Time |
|---------|---------|---------------|--------------|
| `--limit 50` (default) | 50 | 2 | ~1s |
| `--limit 100` | 100 | 4 | ~2s |
| `--limit 0` (all) | 502 | 21 | ~10-20s |
| `--page 1` | 25 | 1 | ~0.5s |

## Configuration

### Config File
Default location: `~/.config/reqtrac/config.json`

**Example:**
```json
{
  "username": "your_username",
  "password": "your_password",
  "base_url": "https://nccaryweb.myvscloud.com"
}
```

### Environment Variables
Environment variables override config file values:
- `REQTRAC_USERNAME` - Override username
- `REQTRAC_PASSWORD` - Override password
- `REQTRAC_BASE_URL` - Override base URL

### Session Storage
Session cookies and CSRF token are stored in: `~/.config/reqtrac/session.json`

This allows you to stay logged in between CLI invocations.

## Output Formats

### Table (default)
Human-readable formatted output.

### JSON
Machine-readable JSON output for scripting.

**Example:**
```bash
./reqtrac programs search --keyword TENNIS -o json | jq '.[] | {name, fmid}'
```

### Raw
Raw HTML output for debugging or custom parsing.

**Example:**
```bash
./reqtrac programs search --keyword TENNIS -o raw > results.html
```

## Common Workflows

### Register for a Program

1. **Login:**
```bash
./reqtrac auth login
```

2. **Search for programs:**
```bash
./reqtrac programs search --keyword TENNIS --age 12
```

3. **Get program details:**
```bash
./reqtrac programs get 12345
```

4. **Add to cart with dates:**
```bash
./reqtrac cart add 12345 \
  --begin-date "07/13/2026" \
  --begin-time "43200" \
  --end-date "07/17/2026" \
  --end-time "46800"
```

5. **View cart and checkout:**
```bash
./reqtrac cart view
./reqtrac cart checkout
```

### Script Integration

You can use the CLI in shell scripts:

```bash
#!/bin/bash

# Login
./reqtrac auth login

# Search and extract program IDs
PROGRAM_IDS=$(./reqtrac programs search --keyword TENNIS -o json | jq -r '.[].fmid')

# Add first program to wishlist
FIRST_ID=$(echo "$PROGRAM_IDS" | head -1)
./reqtrac wishlist add "$FIRST_ID"

echo "Added program $FIRST_ID to wishlist"
```

## Troubleshooting

### Cloudflare 403 Errors
The requests-based client may be blocked by Cloudflare. Solutions:
- Use a VPN or different network
- Run from the same network as the browser that works
- Consider implementing the Playwright client (not included in this CLI)

### Authentication Issues
If login fails:
1. Check credentials: `./reqtrac config show`
2. Clear session: `./reqtrac auth logout`
3. Try logging in again: `./reqtrac auth login`
4. Enable verbose mode: `./reqtrac -v auth login`

### Session Expired
If you get authentication errors:
```bash
./reqtrac auth logout
./reqtrac auth login
```

## Architecture

### Directory Structure
```
cary_reqtrac_shopping/
├── api_client.py          # Core API client (requests-based)
├── config.py              # Configuration management
├── session.py             # Session persistence
├── cli/
│   ├── __init__.py
│   ├── main.py            # Main CLI entry point
│   ├── auth.py            # Authentication commands
│   ├── programs.py        # Program search commands
│   ├── wishlist.py        # Wishlist commands
│   ├── cart.py            # Cart commands
│   └── config_cmd.py      # Config commands
├── reqtrac.py             # Standalone entry point script
└── requirements.txt       # Dependencies
```

### Data Flow
1. **Login** → Save session cookies + CSRF token to `~/.config/reqtrac/session.json`
2. **Commands** → Load session from file, make API calls
3. **Logout** → Clear session file

### Dependencies
- **requests** - HTTP client
- **beautifulsoup4** - HTML parsing
- **click** - CLI framework
- **rich** - Terminal formatting (optional, for enhanced output)

## Development

### Adding New Commands

1. Create command module in `cli/` directory
2. Define Click command group
3. Register in `cli/main.py`
4. Use `get_authenticated_client()` helper for API access

**Example:**
```python
# cli/my_commands.py
@click.group()
def mycommands():
    """My custom commands."""
    pass

@mycommands.command()
def myaction():
    """Do something."""
    client = get_authenticated_client()
    # Use client...
```

### Testing
Test individual commands:
```bash
# Enable verbose logging
./reqtrac -v programs search --keyword TEST

# Test with different output formats
./reqtrac programs search --keyword TEST -o json
./reqtrac programs search --keyword TEST -o raw
```

## License

See parent project license.
