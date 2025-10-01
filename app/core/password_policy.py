"""
Password policy enforcement for Mandate Vault.
Implements comprehensive password strength requirements.
"""
import re
from typing import Tuple


class PasswordPolicy:
    """
    Enforce password strength requirements.
    
    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not in common passwords list
    """
    
    def __init__(
        self,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True
    ):
        """
        Initialize password policy.
        
        Args:
            min_length: Minimum password length (default: 12)
            require_uppercase: Require uppercase letter (default: True)
            require_lowercase: Require lowercase letter (default: True)
            require_digit: Require digit (default: True)
            require_special: Require special character (default: True)
        """
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.common_passwords = self._load_common_passwords()
    
    def validate(self, password: str) -> Tuple[bool, str]:
        """
        Validate password against policy.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check minimum length
        if len(password) < self.min_length:
            return False, f"Password must be at least {self.min_length} characters long"
        
        # Check maximum length (bcrypt limit)
        if len(password.encode('utf-8')) > 72:
            return False, "Password cannot exceed 72 bytes"
        
        # Check uppercase requirement
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter (A-Z)"
        
        # Check lowercase requirement
        if self.require_lowercase and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter (a-z)"
        
        # Check digit requirement
        if self.require_digit and not re.search(r'\d', password):
            return False, "Password must contain at least one digit (0-9)"
        
        # Check special character requirement
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', password):
            return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>_-+=[]\\\/;'`~)"
        
        # Check against common passwords
        if password.lower() in self.common_passwords:
            return False, "Password is too common. Please choose a more unique password"
        
        # Check for sequential characters
        if self._has_sequential_chars(password):
            return False, "Password cannot contain sequential characters (e.g., '123', 'abc')"
        
        # Check for repeated characters
        if self._has_repeated_chars(password):
            return False, "Password cannot contain more than 3 repeated characters in a row"
        
        return True, "Password meets all requirements"
    
    def get_strength_score(self, password: str) -> int:
        """
        Calculate password strength score (0-100).
        
        Args:
            password: Password to score
            
        Returns:
            Score from 0-100
        """
        score = 0
        
        # Length score (up to 40 points)
        score += min(40, len(password) * 2)
        
        # Character variety (up to 40 points)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;\'`~]', password):
            score += 10
        
        # Entropy score (up to 20 points)
        unique_chars = len(set(password))
        score += min(20, unique_chars)
        
        # Penalties
        if password.lower() in self.common_passwords:
            score -= 30
        if self._has_sequential_chars(password):
            score -= 20
        if self._has_repeated_chars(password):
            score -= 10
        
        return max(0, min(100, score))
    
    def get_strength_label(self, score: int) -> str:
        """
        Get strength label from score.
        
        Args:
            score: Password strength score (0-100)
            
        Returns:
            Strength label (Weak/Fair/Good/Strong/Excellent)
        """
        if score < 40:
            return "Weak"
        elif score < 60:
            return "Fair"
        elif score < 75:
            return "Good"
        elif score < 90:
            return "Strong"
        else:
            return "Excellent"
    
    def _has_sequential_chars(self, password: str) -> bool:
        """Check for sequential characters (123, abc, etc.)."""
        sequences = [
            "0123456789",
            "abcdefghijklmnopqrstuvwxyz",
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm"
        ]
        
        password_lower = password.lower()
        for seq in sequences:
            for i in range(len(seq) - 2):
                if seq[i:i+3] in password_lower or seq[i:i+3][::-1] in password_lower:
                    return True
        return False
    
    def _has_repeated_chars(self, password: str) -> bool:
        """Check for more than 3 repeated characters."""
        for i in range(len(password) - 3):
            if password[i] == password[i+1] == password[i+2] == password[i+3]:
                return True
        return False
    
    def _load_common_passwords(self) -> set:
        """Load common passwords list."""
        # Top 100 most common passwords
        return {
            "password", "123456", "12345678", "1234", "qwerty", "12345", "dragon",
            "pussy", "baseball", "football", "letmein", "monkey", "696969", "abc123",
            "mustang", "michael", "shadow", "master", "jennifer", "111111", "2000",
            "jordan", "superman", "harley", "1234567", "fuckme", "hunter", "fuckyou",
            "trustno1", "ranger", "buster", "thomas", "tigger", "robert", "soccer",
            "fuck", "batman", "test", "pass", "killer", "hockey", "george", "charlie",
            "andrew", "michelle", "love", "sunshine", "jessica", "asshole", "6969",
            "pepper", "daniel", "access", "123456789", "654321", "joshua", "maggie",
            "starwars", "silver", "william", "dallas", "yankees", "123123", "ashley",
            "666666", "hello", "amanda", "orange", "biteme", "freedom", "computer",
            "sexy", "thunder", "nicole", "ginger", "heather", "hammer", "summer",
            "corvette", "taylor", "fucker", "austin", "1111", "merlin", "matthew",
            "121212", "golfer", "cheese", "princess", "martin", "chelsea", "patrick",
            "richard", "diamond", "yellow", "bigdog", "secret", "asdfgh", "sparky",
            "cowboy", "cameron", "winter", "welcome"
        }


# Global instance
password_policy = PasswordPolicy(
    min_length=12,
    require_uppercase=True,
    require_lowercase=True,
    require_digit=True,
    require_special=True
)
