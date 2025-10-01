"""
Security utilities for Mandate Vault.
"""
import re
from typing import Dict, Any, Optional
from enum import Enum


class DataClassification(str, Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class PaymentCardPatterns:
    """Patterns for detecting payment card data."""
    
    # Credit card number patterns (Luhn algorithm required for validation)
    CARD_NUMBER_PATTERN = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
    
    # CVV patterns
    CVV_PATTERN = re.compile(r'\b\d{3,4}\b')
    
    # Expiry date patterns
    EXPIRY_PATTERN = re.compile(r'\b\d{2}[\/\-]\d{2}\b')
    
    # Cardholder name patterns (basic)
    CARDHOLDER_PATTERN = re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b')


class SecurityValidator:
    """Security validation utilities."""
    
    @staticmethod
    def contains_payment_card_data(data: str) -> bool:
        """
        Check if text contains potential payment card data.
        
        Args:
            data: Text to check
            
        Returns:
            True if payment card data is detected
        """
        # Check for card number patterns
        if PaymentCardPatterns.CARD_NUMBER_PATTERN.search(data):
            return True
            
        # Check for CVV patterns
        if PaymentCardPatterns.CVV_PATTERN.search(data):
            return True
            
        # Check for expiry date patterns
        if PaymentCardPatterns.EXPIRY_PATTERN.search(data):
            return True
            
        # Check for cardholder name patterns
        if PaymentCardPatterns.CARDHOLDER_PATTERN.search(data):
            return True
            
        return False
    
    @staticmethod
    def sanitize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize data to remove or mask sensitive information.
        
        Args:
            data: Dictionary containing potentially sensitive data
            
        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Check for payment card data
                if SecurityValidator.contains_payment_card_data(value):
                    sanitized[key] = "[REDACTED - Payment Card Data Detected]"
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = SecurityValidator.sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    SecurityValidator.sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
                
        return sanitized
    
    @staticmethod
    def classify_data(data: Dict[str, Any]) -> DataClassification:
        """
        Classify data based on content analysis.
        
        Args:
            data: Dictionary to classify
            
        Returns:
            Data classification level
        """
        data_str = str(data).lower()
        
        # Check for payment card data (highest sensitivity)
        if SecurityValidator.contains_payment_card_data(data_str):
            return DataClassification.RESTRICTED
            
        # Check for other sensitive patterns
        sensitive_patterns = [
            'password', 'secret', 'token', 'key', 'credential',
            'ssn', 'social security', 'tax id', 'ein',
            'bank account', 'routing number', 'iban',
            'phone', 'email', 'address'
        ]
        
        if any(pattern in data_str for pattern in sensitive_patterns):
            return DataClassification.CONFIDENTIAL
            
        # Check for internal business data
        internal_patterns = [
            'mandate', 'tenant', 'customer', 'user',
            'verification', 'audit', 'log'
        ]
        
        if any(pattern in data_str for pattern in internal_patterns):
            return DataClassification.INTERNAL
            
        return DataClassification.PUBLIC
    
    @staticmethod
    def validate_no_payment_card_data(data: Dict[str, Any]) -> bool:
        """
        Validate that data contains no payment card information.
        
        Args:
            data: Dictionary to validate
            
        Returns:
            True if no payment card data is found
        """
        data_str = str(data)
        return not SecurityValidator.contains_payment_card_data(data_str)


class SecurityMiddleware:
    """Security middleware for request/response processing."""
    
    @staticmethod
    def process_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process request data for security compliance.
        
        Args:
            data: Request data
            
        Returns:
            Processed data
        """
        # Validate no payment card data
        if not SecurityValidator.validate_no_payment_card_data(data):
            raise ValueError("Payment card data is not allowed in requests")
            
        # Sanitize data
        return SecurityValidator.sanitize_data(data)
    
    @staticmethod
    def process_response_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process response data for security compliance.
        
        Args:
            data: Response data
            
        Returns:
            Processed data
        """
        # Sanitize data
        sanitized = SecurityValidator.sanitize_data(data)
        
        # Add data classification
        classification = SecurityValidator.classify_data(sanitized)
        sanitized['_data_classification'] = classification.value
        
        return sanitized


# Global security validator instance
security_validator = SecurityValidator()
security_middleware = SecurityMiddleware()

