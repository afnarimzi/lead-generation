"""
Application-wide constants for the Lead Scraper system.

This module centralizes all configuration constants, default values,
and magic numbers used throughout the application.
"""

# ============================================================================
# CREDIT MANAGEMENT
# ============================================================================

# Default credit limits
DEFAULT_FREE_PLAN_CREDIT_LIMIT = 5.0
DEFAULT_CREDIT_WARNING_THRESHOLD = 80.0  # Percentage
DEFAULT_CREDIT_STOP_THRESHOLD = 95.0     # Percentage

# Credit cost estimates per platform (per result)
CREDIT_COST_PER_RESULT = {
    'upwork': 0.01,
    'freelancer': 0.01,
    'fiverr': 0.01,
    'peopleperhour': 0.01
}


# ============================================================================
# SCRAPING DEFAULTS
# ============================================================================

# Default maximum results per platform
DEFAULT_MAX_RESULTS_PER_PLATFORM = 100

# Default page limit for pagination
DEFAULT_PAGE_LIMIT = 50

# Default time range for job postings (in hours)
DEFAULT_POSTED_WITHIN_HOURS = 168  # 7 days

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 2
DEFAULT_EXPONENTIAL_BACKOFF_BASE = 2


# ============================================================================
# APIFY ACTOR IDS
# ============================================================================

# Default Apify actor IDs for each platform
DEFAULT_APIFY_ACTORS = {
    'upwork': 'flash_mage~upwork',
    'freelancer': 'consummate_mandala~freelancer-project-scraper',
    'fiverr': 'piotrv1001~fiverr-listings-scraper',
    'peopleperhour': 'getdataforme~peopleperhour-job-scraper'
}


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Default database connection pool size
DEFAULT_DATABASE_POOL_SIZE = 10

# Database query timeouts (in seconds)
DEFAULT_QUERY_TIMEOUT = 30

# Batch insert size for bulk operations
DEFAULT_BATCH_INSERT_SIZE = 100


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Default log level
DEFAULT_LOG_LEVEL = 'INFO'

# Default log file path
DEFAULT_LOG_FILE_PATH = 'logs/lead_scraper.log'

# Default log file max size (in MB)
DEFAULT_LOG_MAX_SIZE_MB = 100

# Log rotation backup count
DEFAULT_LOG_BACKUP_COUNT = 5


# ============================================================================
# QUALITY SCORING
# ============================================================================

# Quality score weights
QUALITY_SCORE_WEIGHTS = {
    'budget': 0.3,
    'description_length': 0.2,
    'skills_count': 0.2,
    'client_rating': 0.15,
    'recency': 0.15
}

# Quality score thresholds
QUALITY_SCORE_EXCELLENT = 80.0
QUALITY_SCORE_GOOD = 60.0
QUALITY_SCORE_FAIR = 40.0

# Description length thresholds (characters)
MIN_DESCRIPTION_LENGTH = 100
IDEAL_DESCRIPTION_LENGTH = 500


# ============================================================================
# DEDUPLICATION
# ============================================================================

# Similarity threshold for duplicate detection (0.0 to 1.0)
DUPLICATE_SIMILARITY_THRESHOLD = 0.85

# Title similarity threshold
TITLE_SIMILARITY_THRESHOLD = 0.90


# ============================================================================
# FILTER ENGINE
# ============================================================================

# Default budget range (USD)
DEFAULT_MIN_BUDGET = 0.0
DEFAULT_MAX_BUDGET = 1000000.0

# Keyword matching
KEYWORD_MATCH_MIN_LENGTH = 2  # Minimum keyword length


# ============================================================================
# PLATFORM NAMES
# ============================================================================

PLATFORM_UPWORK = 'Upwork'
PLATFORM_FREELANCER = 'Freelancer'
PLATFORM_FIVERR = 'Fiverr'
PLATFORM_PEOPLEPERHOUR = 'PeoplePerHour'

ALL_PLATFORMS = [
    PLATFORM_UPWORK,
    PLATFORM_FREELANCER,
    PLATFORM_FIVERR,
    PLATFORM_PEOPLEPERHOUR
]


# ============================================================================
# PAYMENT TYPES
# ============================================================================

PAYMENT_TYPE_FIXED = 'fixed'
PAYMENT_TYPE_HOURLY = 'hourly'

VALID_PAYMENT_TYPES = [
    PAYMENT_TYPE_FIXED,
    PAYMENT_TYPE_HOURLY
]


# ============================================================================
# DATE FORMATS
# ============================================================================

# ISO 8601 date format variations
DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%SZ',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d'
]


# ============================================================================
# AUTHENTICATION
# ============================================================================

# Supported authentication methods
AUTH_METHOD_USERNAME_PASSWORD = 'username_password'
AUTH_METHOD_COOKIES = 'cookies'

SUPPORTED_AUTH_METHODS = [
    AUTH_METHOD_USERNAME_PASSWORD,
    AUTH_METHOD_COOKIES
]

# Platforms that support authentication
AUTH_SUPPORTED_PLATFORMS = [
    'upwork',
    'freelancer',
    'fiverr',
    'peopleperhour'
]


# ============================================================================
# EXPORT FORMATS
# ============================================================================

EXPORT_FORMAT_CSV = 'csv'
EXPORT_FORMAT_JSON = 'json'
EXPORT_FORMAT_EXCEL = 'excel'

SUPPORTED_EXPORT_FORMATS = [
    EXPORT_FORMAT_CSV,
    EXPORT_FORMAT_JSON,
    EXPORT_FORMAT_EXCEL
]


# ============================================================================
# HTTP CONFIGURATION
# ============================================================================

# HTTP request timeout (in seconds)
HTTP_REQUEST_TIMEOUT = 30

# User agent for web scraping
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Rate limiting (requests per second)
DEFAULT_RATE_LIMIT = 2


# ============================================================================
# BUDGET ENRICHMENT
# ============================================================================

# Budget extraction patterns
BUDGET_PATTERNS = {
    'inr': r'₹([\d,]+(?:\.\d{2})?)\s*-\s*([\d,]+(?:\.\d{2})?)\s*INR',
    'inr_with_symbol': r'₹([\d,]+(?:\.\d{2})?)\s*-\s*₹([\d,]+(?:\.\d{2})?)\s*INR',
    'usd': r'\$([\d,]+(?:\.\d{2})?)\s*-\s*([\d,]+(?:\.\d{2})?)\s*USD',
    'usd_with_symbol': r'\$([\d,]+(?:\.\d{2})?)\s*-\s*\$([\d,]+(?:\.\d{2})?)\s*USD'
}

# Enrichment rate limiting (seconds between requests)
ENRICHMENT_DELAY_SECONDS = 2

# Maximum enrichment batch size
MAX_ENRICHMENT_BATCH_SIZE = 50


# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_INVALID_CONFIG = "Invalid configuration"
ERROR_MISSING_CREDENTIALS = "Missing authentication credentials"
ERROR_DATABASE_CONNECTION = "Database connection failed"
ERROR_APIFY_TOKEN_MISSING = "Apify token not configured"
ERROR_ACTOR_NOT_FOUND = "Apify actor not found"
ERROR_SCRAPING_FAILED = "Scraping operation failed"
ERROR_NORMALIZATION_FAILED = "Lead normalization failed"


# ============================================================================
# SUCCESS MESSAGES
# ============================================================================

SUCCESS_SCRAPING_COMPLETE = "Scraping completed successfully"
SUCCESS_DATABASE_SAVE = "Leads saved to database"
SUCCESS_EXPORT_COMPLETE = "Export completed successfully"
SUCCESS_AUTH_CONFIGURED = "Authentication configured"
