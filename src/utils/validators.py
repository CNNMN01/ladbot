"""
Input validation utilities
"""

import re
from typing import Any, Optional, Union
from discord.ext import commands


class ValidationError(commands.CommandError):
    """Custom validation error"""
    pass


def validate_boolean_input(value: str) -> bool:
    """Validate and convert boolean input"""
    true_values = ["yes", "y", "true", "t", "1", "enable", "on"]
    false_values = ["no", "n", "false", "f", "0", "disable", "off"]

    value_lower = value.lower()

    if value_lower in true_values:
        return True
    elif value_lower in false_values:
        return False
    else:
        raise ValidationError(f"'{value}' is not a valid boolean value. Use: {', '.join(true_values + false_values)}")


def validate_integer_input(value: str, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """Validate and convert integer input"""
    try:
        int_value = int(value)
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid integer.")

    if min_val is not None and int_value < min_val:
        raise ValidationError(f"Value must be at least {min_val}.")

    if max_val is not None and int_value > max_val:
        raise ValidationError(f"Value must be at most {max_val}.")

    return int_value


def validate_url(url: str) -> bool:
    """Validate URL format"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return url_pattern.match(url) is not None


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Sanitize text input"""
    # Remove any potential harmful characters
    sanitized = re.sub(r'[^\w\s\-_.,!?@#$%^&*()+=]', '', text)

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length - 3] + "..."

    return sanitized