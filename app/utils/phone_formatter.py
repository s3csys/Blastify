"""Phone number formatting utilities."""

import re
import phonenumbers
import logging

logger = logging.getLogger(__name__)

def format_phone_for_whatsapp(phone):
    """Format a phone number for WhatsApp API.
    
    Args:
        phone: The phone number to format
        
    Returns:
        Formatted phone number or None if invalid
    """
    try:
        # Remove any non-digit characters except the plus sign
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Ensure the number has a plus sign
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        
        # Parse the phone number
        parsed = phonenumbers.parse(cleaned, None)
        
        # Check if the number is valid
        if not phonenumbers.is_valid_number(parsed):
            return None
        
        # Format in E.164 format (required by WhatsApp)
        formatted = phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        )
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting phone number: {str(e)}")
        return None

def get_country_code(phone):
    """Extract the country code from a phone number.
    
    Args:
        phone: The phone number
        
    Returns:
        Country code or None if invalid
    """
    try:
        # Parse the phone number
        parsed = phonenumbers.parse(phone, None)
        
        # Get the country code
        return str(parsed.country_code)
        
    except Exception as e:
        logger.error(f"Error getting country code: {str(e)}")
        return None