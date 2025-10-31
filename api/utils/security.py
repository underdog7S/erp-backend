"""
Security utilities for input validation and sanitization
"""
import re
from html import escape
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def sanitize_string(value, max_length=None, allow_html=False):
    """
    Sanitize string input to prevent XSS attacks
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        allow_html: If False, strip all HTML tags
    
    Returns:
        Sanitized string
    """
    if not value:
        return None
    
    value = str(value)
    
    # Remove HTML tags if not allowed
    if not allow_html:
        value = re.sub(r'<[^>]+>', '', value)
    
    # Escape HTML entities
    value = escape(value)
    
    # Trim whitespace
    value = value.strip()
    
    # Limit length
    if max_length and len(value) > max_length:
        logger.warning(f"String truncated from {len(value)} to {max_length} characters")
        value = value[:max_length]
    
    return value


def validate_email(email):
    """
    Validate email format
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, raises ValidationError otherwise
    """
    if not email:
        raise ValidationError("Email is required")
    
    email = email.strip().lower()
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format")
    
    # Check length
    if len(email) > 254:  # RFC 5321 limit
        raise ValidationError("Email address too long")
    
    return email


def validate_phone(phone):
    """
    Validate phone number format
    
    Args:
        phone: Phone number to validate
    
    Returns:
        Cleaned phone number or None
    """
    if not phone:
        return None
    
    # Remove all non-digits
    digits_only = re.sub(r'\D', '', str(phone))
    
    # Check if it's a valid length (10-15 digits)
    if not (10 <= len(digits_only) <= 15):
        raise ValidationError("Phone number must be between 10 and 15 digits")
    
    return digits_only


def validate_amount(amount, min_value=0, max_value=999999999):
    """
    Validate monetary amount
    
    Args:
        amount: Amount to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
    
    Returns:
        Validated amount as float
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        raise ValidationError("Invalid amount format")
    
    if amount < min_value:
        raise ValidationError(f"Amount must be at least {min_value}")
    
    if amount > max_value:
        raise ValidationError(f"Amount cannot exceed {max_value}")
    
    # Round to 2 decimal places
    return round(amount, 2)


def validate_date(date_string):
    """
    Validate date string format (YYYY-MM-DD)
    
    Args:
        date_string: Date string to validate
    
    Returns:
        Validated date string
    """
    if not date_string:
        return None
    
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, str(date_string)):
        raise ValidationError("Date must be in YYYY-MM-DD format")
    
    return date_string


def validate_url(url):
    """
    Validate URL format
    
    Args:
        url: URL to validate
    
    Returns:
        Validated URL
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Basic URL pattern
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    
    if not re.match(pattern, url):
        raise ValidationError("Invalid URL format")
    
    # Ensure it's HTTPS in production
    if url.startswith('http://') and not url.startswith('http://localhost'):
        logger.warning(f"Non-HTTPS URL detected: {url}")
    
    return url


def validate_academic_year(year_string):
    """
    Validate academic year format (e.g., 2024-25)
    
    Args:
        year_string: Academic year string
    
    Returns:
        Validated academic year
    """
    if not year_string:
        return None
    
    year_string = year_string.strip()
    
    pattern = r'^\d{4}-\d{2}$'
    if not re.match(pattern, year_string):
        raise ValidationError("Academic year must be in format YYYY-YY (e.g., 2024-25)")
    
    return year_string


def prevent_sql_injection(query_string):
    """
    Basic check for SQL injection patterns
    
    Note: Django ORM already protects against SQL injection.
    This is an additional safety check for raw queries.
    """
    dangerous_patterns = [
        r"';.*--",
        r"'.*or.*'",
        r"'.*OR.*'",
        r"'.*AND.*'",
        r"'.*UNION.*'",
        r"'.*DROP.*'",
        r"'.*DELETE.*'",
        r"'.*UPDATE.*'",
        r"'.*INSERT.*'",
        r"<script",
        r"javascript:",
    ]
    
    query_lower = query_string.lower()
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query_lower):
            logger.warning(f"Potential SQL injection detected: {pattern}")
            raise ValidationError("Invalid input detected")
    
    return query_string


def validate_file_name(file_name):
    """
    Validate file name to prevent directory traversal
    
    Args:
        file_name: File name to validate
    
    Returns:
        Validated file name
    """
    if not file_name:
        raise ValidationError("File name is required")
    
    # Remove path components
    file_name = file_name.replace('\\', '/').split('/')[-1]
    
    # Check for dangerous characters
    dangerous_chars = ['..', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        if char in file_name:
            raise ValidationError(f"File name contains invalid character: {char}")
    
    # Limit length
    if len(file_name) > 255:
        raise ValidationError("File name too long")
    
    return file_name

