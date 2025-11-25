"""Jinja2 template filters and custom filters."""
from datetime import datetime
from typing import Any, Optional


def format_currency(value: float, currency: str = "USD") -> str:
    """
    Format a number as currency.
    
    Args:
        value: Numeric value
        currency: Currency code (USD, EUR, etc.)
        
    Returns:
        Formatted currency string
    """
    if value is None:
        return ""
    
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "INR": "₹"
    }
    
    symbol = currency_symbols.get(currency, currency + " ")
    return f"{symbol}{value:,.2f}"


def format_date(value: Optional[datetime], format: str = "%Y-%m-%d") -> str:
    """
    Format a datetime object.
    
    Args:
        value: Datetime object
        format: strftime format string
        
    Returns:
        Formatted date string
    """
    if value is None:
        return ""
    
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value
    
    return value.strftime(format)


def format_datetime(value: Optional[datetime], format: str = "%Y-%m-%d %H:%M") -> str:
    """
    Format a datetime with time.
    
    Args:
        value: Datetime object
        format: strftime format string
        
    Returns:
        Formatted datetime string
    """
    return format_date(value, format)


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format a number as percentage.
    
    Args:
        value: Numeric value (0-1 or 0-100)
        decimals: Decimal places
        
    Returns:
        Formatted percentage string
    """
    if value is None:
        return ""
    
    # Assume if value > 1, it's already a percentage
    if value > 1:
        return f"{value:.{decimals}f}%"
    else:
        return f"{value * 100:.{decimals}f}%"


def truncate_string(value: str, length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a string to specified length.
    
    Args:
        value: String to truncate
        length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if not value:
        return ""
    
    if len(value) <= length:
        return value
    
    return value[:length - len(suffix)] + suffix


def format_number(value: float, decimals: int = 2) -> str:
    """
    Format a number with thousands separator.
    
    Args:
        value: Numeric value
        decimals: Decimal places
        
    Returns:
        Formatted number string
    """
    if value is None:
        return ""
    
    return f"{value:,.{decimals}f}"


def time_ago(value: datetime) -> str:
    """
    Convert datetime to human-readable "time ago" format.
    
    Args:
        value: Datetime object
        
    Returns:
        Human-readable time ago string
    """
    if not value:
        return ""
    
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value
    
    now = datetime.utcnow()
    diff = now - value
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"


def register_filters(app):
    """
    Register custom Jinja2 filters with Flask app.
    
    Args:
        app: Flask application instance
    """
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['date'] = format_date
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['percentage'] = format_percentage
    app.jinja_env.filters['truncate_str'] = truncate_string
    app.jinja_env.filters['number'] = format_number
    app.jinja_env.filters['timeago'] = time_ago
