"""
ACP (Authorization Credential Protocol) Pydantic schemas.

Defines data models for ACP delegated tokens with strict validation.
"""
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ACPConstraints(BaseModel):
    """
    ACP constraint object.
    
    Defines limits and restrictions on the authorization.
    """
    merchant: Optional[str] = Field(None, description="Merchant identifier constraint")
    item: Optional[str] = Field(None, description="Item/product constraint")
    category: Optional[str] = Field(None, description="Category constraint")
    location: Optional[str] = Field(None, description="Geographic location constraint")
    time_window: Optional[Dict[str, Any]] = Field(None, description="Time window constraint")
    
    model_config = ConfigDict(
        extra='allow',  # Allow additional constraint types
        str_strip_whitespace=True
    )


class ACPDelegatedToken(BaseModel):
    """
    ACP Delegated Token schema.
    
    Represents an authorization credential in the ACP protocol format.
    
    Attributes:
        token_id: Unique identifier for this token
        psp_id: Payment Service Provider identifier
        merchant_id: Merchant identifier
        max_amount: Maximum authorized amount
        currency: ISO 4217 currency code (USD, EUR, etc.)
        expires_at: Token expiration timestamp
        constraints: Additional constraints on the authorization
    
    Example:
        >>> token = ACPDelegatedToken(
        ...     token_id="acp-token-123",
        ...     psp_id="psp-456",
        ...     merchant_id="merchant-789",
        ...     max_amount=Decimal("5000.00"),
        ...     currency="USD",
        ...     expires_at=datetime(2026, 1, 1),
        ...     constraints={"merchant": "acme-corp", "category": "retail"}
        ... )
    """
    
    # Required fields
    token_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique token identifier"
    )
    
    psp_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Payment Service Provider identifier"
    )
    
    merchant_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Merchant identifier"
    )
    
    max_amount: Decimal = Field(
        ...,
        ge=Decimal("0.01"),
        decimal_places=2,
        description="Maximum authorized amount (must be positive)"
    )
    
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (e.g., USD, EUR)"
    )
    
    expires_at: datetime = Field(
        ...,
        description="Token expiration timestamp (must be in the future)"
    )
    
    # Optional fields
    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional authorization constraints"
    )
    
    # Pydantic v2 configuration
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        extra='forbid',  # Strict: reject unknown fields
        frozen=False
    )
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """
        Validate currency code format.
        
        Args:
            v: Currency code
        
        Returns:
            Uppercase currency code
        
        Raises:
            ValueError: If currency code is invalid
        """
        v = v.upper().strip()
        
        # Check format (must be 3 uppercase letters)
        if not v.isalpha() or len(v) != 3:
            raise ValueError(
                f"Currency must be a 3-letter ISO 4217 code (e.g., USD, EUR). Got: {v}"
            )
        
        # Optional: Validate against known currency codes
        valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD',
            'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN',
            'INR', 'CNY', 'HKD', 'SGD', 'KRW', 'BRL', 'MXN', 'ZAR',
            'AED', 'SAR', 'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'ILS',
            'TRY', 'RUB', 'THB', 'MYR', 'IDR', 'PHP', 'VND', 'PKR'
        }
        
        if v not in valid_currencies:
            raise ValueError(
                f"Currency code '{v}' is not a recognized ISO 4217 code. "
                f"If this is a valid currency, it may need to be added to the allowed list."
            )
        
        return v
    
    @field_validator('expires_at')
    @classmethod
    def validate_expiration(cls, v: datetime) -> datetime:
        """
        Validate that expiration is in the future.
        
        Args:
            v: Expiration datetime
        
        Returns:
            Validated datetime
        
        Raises:
            ValueError: If expiration is in the past
        """
        now = datetime.now(v.tzinfo) if v.tzinfo else datetime.utcnow()
        
        if v <= now:
            raise ValueError(
                f"expires_at must be in the future. "
                f"Got: {v.isoformat()}, Current: {now.isoformat()}"
            )
        
        return v
    
    @field_validator('token_id', 'psp_id', 'merchant_id')
    @classmethod
    def validate_identifiers(cls, v: str) -> str:
        """
        Validate identifier format.
        
        Args:
            v: Identifier string
        
        Returns:
            Validated identifier
        
        Raises:
            ValueError: If identifier contains invalid characters
        """
        v = v.strip()
        
        if not v:
            raise ValueError("Identifier cannot be empty or whitespace")
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '\\', '\n', '\r', '\x00']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(
                    f"Identifier contains invalid character: {repr(char)}"
                )
        
        return v
    
    @field_validator('max_amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """
        Validate amount has max 2 decimal places.
        
        Args:
            v: Amount value
        
        Returns:
            Validated amount
        
        Raises:
            ValueError: If amount has more than 2 decimal places
        """
        # Check decimal places
        if v.as_tuple().exponent < -2:
            raise ValueError(
                f"max_amount can have at most 2 decimal places. Got: {v}"
            )
        
        # Check reasonable limits (prevent overflow)
        max_limit = Decimal("999999999999.99")  # ~1 trillion
        if v > max_limit:
            raise ValueError(
                f"max_amount exceeds maximum limit of {max_limit}"
            )
        
        return v
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ACPDelegatedToken":
        """
        Create ACPDelegatedToken from dictionary with strict validation.
        
        Args:
            data: Dictionary containing token data
        
        Returns:
            ACPDelegatedToken instance
        
        Raises:
            ValueError: If validation fails
            KeyError: If required fields are missing
        
        Example:
            >>> data = {
            ...     'token_id': 'acp-123',
            ...     'psp_id': 'psp-456',
            ...     'merchant_id': 'merchant-789',
            ...     'max_amount': '5000.00',
            ...     'currency': 'USD',
            ...     'expires_at': '2026-01-01T00:00:00Z',
            ...     'constraints': {'category': 'retail'}
            ... }
            >>> token = ACPDelegatedToken.from_dict(data)
        """
        try:
            # Pydantic v2: model_validate is the new method
            return cls.model_validate(data)
        except Exception as e:
            # Provide more detailed error message
            raise ValueError(
                f"Failed to create ACPDelegatedToken from dict: {str(e)}"
            ) from e
    
    def to_authorization_data(self) -> Dict[str, Any]:
        """
        Convert to Authorization model format.
        
        Returns:
            Dictionary suitable for creating Authorization model
        
        Example:
            >>> token = ACPDelegatedToken(...)
            >>> auth_data = token.to_authorization_data()
            >>> authorization = Authorization(**auth_data)
        """
        # Use model_dump(mode='json') to properly serialize Decimal and datetime objects
        raw_payload = self.model_dump(mode='json')
        
        # Convert constraints to dict for scope field
        constraints_dict = self.constraints.model_dump() if self.constraints else {}
        
        return {
            'protocol': 'ACP',
            'issuer': self.psp_id,
            'subject': self.merchant_id,
            'scope': {'constraints': constraints_dict} if constraints_dict else {},
            'amount_limit': self.max_amount,  # Decimal is OK for SQLAlchemy Numeric column
            'currency': self.currency,
            'expires_at': self.expires_at,  # datetime is OK for SQLAlchemy DateTime column
            'status': 'ACTIVE',
            'raw_payload': raw_payload  # JSON-serializable dict
        }
    
    def to_json(self) -> str:
        """
        Convert to JSON string.
        
        Returns:
            JSON string representation
        """
        return self.model_dump_json()

