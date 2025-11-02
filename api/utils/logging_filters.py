"""
Custom logging filters for Django
Suppress HTTPS protocol errors in development
"""
import logging
import sys
from django.conf import settings

# Monkey patch to suppress basehttp HTTPS errors in development
if settings.DEBUG:
    # Store original write methods
    _original_stderr_write = sys.stderr.write
    _original_stdout_write = sys.stdout.write
    
    def _filter_stderr_write(text):
        """Filter stderr writes to suppress HTTPS errors"""
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        
        if isinstance(text, str):
            # Suppress HTTPS-related error messages
            if any(keyword in text for keyword in [
                'You\'re accessing the development server over HTTPS',
                'Bad request version',
                'basehttp',
            ]):
                return  # Suppress this write
            else:
                return _original_stderr_write(text)
        else:
            return _original_stderr_write(text)
    
    # Note: We're not patching stderr directly as it can break other things
    # Instead, we rely on the logging filter


class SuppressHTTPSErrorsFilter(logging.Filter):
    """
    Filter to suppress HTTPS errors in development mode
    Suppresses both INFO and ERROR messages related to HTTPS/HTTP protocol issues
    """
    
    def filter(self, record):
        # Only suppress in development mode
        if not settings.DEBUG:
            return True
        
        # Get logger name - check all possible attributes
        logger_name = getattr(record, 'name', '') or getattr(record, 'logger', '') or ''
        
        # Check if this is from basehttp or django.server loggers
        # Match any logger containing these keywords
        if any(name in logger_name.lower() for name in [
            'basehttp',
            'django.server',
            'django.core.servers',
            'servers.basehttp',
        ]) or 'basehttp' in str(record):
            try:
                # Try to get message from record
                message = ''
                if hasattr(record, 'getMessage'):
                    message = record.getMessage()
                elif hasattr(record, 'msg'):
                    message = str(record.msg)
                    if hasattr(record, 'args') and record.args:
                        try:
                            message = message % record.args
                        except:
                            message = str(record.msg) + ' ' + str(record.args)
                
                # Suppress messages related to HTTPS/HTTP protocol issues
                message_lower = message.lower()
                if any(keyword in message_lower for keyword in [
                    'https',
                    'bad request version',
                    'you\'re accessing',
                    'request version',
                    'development server over https',
                ]):
                    # Suppress this log record
                    return False
            except Exception as e:
                # If we can't get the message, check record attributes directly
                # Just suppress all basehttp messages in development to be safe
                if 'basehttp' in logger_name.lower():
                    return False
        
        # Allow all other log records
        return True

