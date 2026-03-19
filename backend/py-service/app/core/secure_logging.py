"""Secure Logging Configuration

Ensures logs never contain sensitive data through filtering and sanitization.
"""

import logging
import re
import json
from typing import Any, Optional
from logging import Filter, Formatter

from app.core.security_hardening import sanitize_log_data, sanitize_metadata, sanitize_ip_address


class SensitiveDataFilter(Filter):
    """Filter to sanitize sensitive data from log records"""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = [
        r'password["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'passcode["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'pass["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'token["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'api_key["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'secret["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'access_token["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'refresh_token["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'authorization["\']?\s*[:=]\s*["\']?Bearer\s+([^\s"\']+)',
        r'credit_card["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'ssn["\']?\s*[:=]\s*["\']?([^"\']+)',
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and sanitize log record"""
        # Sanitize message
        if hasattr(record, 'msg') and record.msg:
            record.msg = self._sanitize_string(str(record.msg))
        
        # Sanitize args
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitize_string(arg))
                elif isinstance(arg, dict):
                    sanitized_args.append(sanitize_metadata(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        # Sanitize extra fields
        if hasattr(record, '__dict__'):
            for key in list(record.__dict__.keys()):
                value = record.__dict__[key]
                if isinstance(value, str):
                    record.__dict__[key] = self._sanitize_string(value)
                elif isinstance(value, dict):
                    record.__dict__[key] = sanitize_metadata(value)
        
        return True
    
    def _sanitize_string(self, text: str) -> str:
        """Sanitize string for sensitive data"""
        # Apply all sensitive patterns
        for pattern in self.SENSITIVE_PATTERNS:
            text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)
            # Replace the captured group with ***
            text = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), "***"), text, flags=re.IGNORECASE)
        
        # General sanitization
        text = sanitize_log_data(text)
        
        return text


class SecureJSONFormatter(Formatter):
    """JSON formatter that sanitizes sensitive data"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with sanitization"""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_log_data(record.getMessage()),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present (sanitized)
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_data["exception"] = sanitize_log_data(exc_text)
        
        # Add extra fields (sanitized)
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
            ]:
                if isinstance(value, str):
                    log_data[key] = sanitize_log_data(value)
                elif isinstance(value, dict):
                    log_data[key] = sanitize_metadata(value)
                else:
                    log_data[key] = value
        
        return json.dumps(log_data)


class SecureTextFormatter(Formatter):
    """Text formatter that sanitizes sensitive data"""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        if fmt is None:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        if datefmt is None:
            datefmt = "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt, datefmt)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sanitization"""
        # Sanitize message
        original_msg = record.msg
        original_args = record.args
        
        if isinstance(record.msg, str):
            record.msg = sanitize_log_data(record.msg)
        elif record.args:
            sanitized_args = tuple(
                sanitize_log_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
            record.msg = record.msg % sanitized_args
            record.args = ()
        
        formatted = super().format(record)
        
        # Restore original for exception formatting
        record.msg = original_msg
        record.args = original_args
        
        # Sanitize exception text if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            formatted = formatted.replace(exc_text, sanitize_log_data(exc_text))
        
        return formatted


def setup_secure_logging() -> logging.Logger:
    """Setup logging with sensitive data filtering"""
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    
    # Set formatter based on configuration
    from app.config import settings
    
    if settings.LOG_FORMAT.lower() == "json":
        formatter = SecureJSONFormatter()
    else:
        formatter = SecureTextFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set log level
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Apply filter to all loggers
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        if not any(isinstance(f, SensitiveDataFilter) for f in logger.filters):
            logger.addFilter(sensitive_filter)
    
    return root_logger

