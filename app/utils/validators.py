"""Validation utilities for request data."""

import re
import logging
from .phone_formatter import format_phone_for_whatsapp

logger = logging.getLogger(__name__)

def validate_phone_number(phone):
    """Validate and format a phone number for WhatsApp.
    
    Args:
        phone: The phone number to validate
        
    Returns:
        Dictionary with validation result and formatted phone number
    """
    # Remove any non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if the number has a reasonable length
    if len(digits_only) < 10 or len(digits_only) > 15:
        return {
            'status': 'failed',
            'error': 'Invalid phone number length'
        }
    
    # Use the phone formatter to get a properly formatted number
    formatted = format_phone_for_whatsapp(phone)
    if not formatted:
        return {
            'status': 'failed',
            'error': 'Invalid phone number format'
        }
    
    return {
        'status': 'success',
        'phone': formatted
    }

def validate_message_request(data):
    """Validate message request data.
    
    Args:
        data: The request data to validate
        
    Returns:
        Dictionary with validation result or list of error messages (for backward compatibility)
    """
    # For backward compatibility
    if isinstance(data, dict) and data.get('_use_new_format', False):
        return validate_message_request_new(data)
    
    errors = []
    
    # Check required fields
    if not data.get('recipient'):
        errors.append('Recipient is required')
    
    if not data.get('message'):
        errors.append('Message text is required')
    
    # Validate platform
    platform = data.get('platform', 'whatsapp').lower()
    if platform not in ['whatsapp', 'telegram']:
        errors.append(f'Unsupported platform: {platform}')
    
    # Platform-specific validation
    if platform == 'whatsapp':
        # Validate phone number format
        phone = data.get('recipient', '')
        if not re.match(r'^\+?[1-9]\d{1,14}$', phone):
            errors.append('Invalid phone number format')
    
    # Validate media URL if provided
    if data.get('media_url'):
        url = data.get('media_url')
        if not url.startswith(('http://', 'https://')):
            errors.append('Media URL must be a valid HTTP/HTTPS URL')
    
    return errors

def validate_message_request_new(data):
    """Validate a message request with the new format.
    
    Args:
        data: The request data to validate
        
    Returns:
        Dictionary with validation result
    """
    # Check required fields
    if not data:
        return {'status': 'failed', 'error': 'No data provided'}
    
    if 'recipient' not in data:
        return {'status': 'failed', 'error': 'Recipient is required'}
    
    if 'message' not in data and 'media_url' not in data:
        return {'status': 'failed', 'error': 'Message or media URL is required'}
    
    # Validate phone number
    phone_result = validate_phone_number(data['recipient'])
    if phone_result['status'] == 'failed':
        return phone_result
    
    # Update the recipient with the formatted phone number
    data['recipient'] = phone_result['phone']
    
    # Validate message length
    if 'message' in data and len(data['message']) > 4096:
        return {'status': 'failed', 'error': 'Message too long (max 4096 characters)'}
    
    # Validate media URL if provided
    if 'media_url' in data and data['media_url']:
        if not data['media_url'].startswith(('http://', 'https://')):
            return {'status': 'failed', 'error': 'Invalid media URL'}
    
    return {'status': 'success'}