"""
JWT-VC verification utilities.
"""
import json
import jwt
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from app.core.config import settings


class JWTVerificationError(Exception):
    """Custom exception for JWT verification errors."""
    pass


def parse_jwt_token(token: str) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    Parse JWT token and return header, payload, and signature.
    
    Args:
        token: JWT token string
        
    Returns:
        Tuple of (header, payload, signature)
        
    Raises:
        JWTVerificationError: If token is invalid
    """
    try:
        # Decode without verification to get payload
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Split token to get signature part
        parts = token.split('.')
        if len(parts) != 3:
            raise JWTVerificationError("Invalid JWT format")
            
        return header, payload, parts[2]
    except Exception as e:
        raise JWTVerificationError(f"Failed to parse JWT: {str(e)}")


def verify_jwt_structure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify basic JWT-VC structure and extract mandate information.
    
    Args:
        payload: JWT payload dictionary
        
    Returns:
        Dictionary with verification results and extracted data
        
    Raises:
        JWTVerificationError: If structure is invalid
    """
    verification_result = {
        "is_valid": False,
        "errors": [],
        "warnings": [],
        "extracted_data": {}
    }
    
    try:
        # Check required fields for JWT-VC
        required_fields = ["iss", "sub", "iat", "exp"]
        for field in required_fields:
            if field not in payload:
                verification_result["errors"].append(f"Missing required field: {field}")
        
        # Check VC-specific fields
        if "vc" not in payload:
            verification_result["warnings"].append("Missing VC field - may not be a Verifiable Credential")
        
        # Extract mandate information
        extracted_data = {
            "issuer_did": payload.get("iss"),
            "subject_did": payload.get("sub"),
            "issued_at": payload.get("iat"),
            "expires_at": payload.get("exp"),
            "scope": payload.get("scope"),
            "amount_limit": payload.get("amount_limit"),
            "credential_type": None,
            "credential_subject": None
        }
        
        # Extract VC-specific data if present
        if "vc" in payload:
            vc_data = payload["vc"]
            extracted_data["credential_type"] = vc_data.get("type")
            extracted_data["credential_subject"] = vc_data.get("credentialSubject")
        
        # Check expiration
        if "exp" in payload:
            exp_timestamp = payload["exp"]
            if datetime.now().timestamp() > exp_timestamp:
                verification_result["warnings"].append("Credential has expired")
                extracted_data["status"] = "expired"
            else:
                extracted_data["status"] = "active"
        else:
            extracted_data["status"] = "active"
        
        # Generate mandate ID from issuer and subject
        if extracted_data["issuer_did"] and extracted_data["subject_did"]:
            extracted_data["mandate_id"] = f"{extracted_data['issuer_did']}:{extracted_data['subject_did']}"
        else:
            extracted_data["mandate_id"] = payload.get("jti", f"mandate_{datetime.now().timestamp()}")
        
        verification_result["extracted_data"] = extracted_data
        
        # If no critical errors, mark as valid
        if not verification_result["errors"]:
            verification_result["is_valid"] = True
            
    except Exception as e:
        verification_result["errors"].append(f"Verification error: {str(e)}")
    
    return verification_result


def verify_jwt_vc(token: str) -> Dict[str, Any]:
    """
    Complete JWT-VC verification process.
    
    Args:
        token: JWT-VC token string
        
    Returns:
        Dictionary with verification results and extracted data
    """
    try:
        # Parse token
        header, payload, signature = parse_jwt_token(token)
        
        # Verify structure
        verification_result = verify_jwt_structure(payload)
        
        # Add parsing information
        verification_result["parsed_payload"] = payload
        verification_result["header"] = header
        
        return verification_result
        
    except JWTVerificationError as e:
        return {
            "is_valid": False,
            "errors": [str(e)],
            "warnings": [],
            "extracted_data": {},
            "parsed_payload": None,
            "header": None
        }
