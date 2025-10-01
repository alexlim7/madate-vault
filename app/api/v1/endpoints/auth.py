"""
Authentication API endpoints.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.auth import (
    AuthService, LoginRequest, TokenResponse, User, 
    get_current_active_user, UserRole
)
from app.core.login_protection import login_protection
from app.core.security_logging import security_log

router = APIRouter()


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return access/refresh tokens.
    Protected against brute force attacks with rate limiting.
    """
    try:
        # Check if account is locked out
        if login_protection.is_locked_out(login_data.email):
            remaining = login_protection.get_lockout_remaining_seconds(login_data.email)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Account locked for {remaining} seconds."
            )
        
        auth_service = AuthService(db)
        
        # Authenticate user
        user = await auth_service.authenticate_user(login_data.email, login_data.password)
        
        # Get client IP for logging
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")
        
        if not user:
            # Record failed attempt
            login_protection.record_failed_login(login_data.email)
            attempts_remaining = login_protection.max_attempts - login_protection.get_failed_attempts_count(login_data.email)
            
            # Log failed authentication
            security_log.log_auth_failure(
                email=login_data.email,
                ip_address=client_ip,
                reason="Invalid credentials",
                attempts_remaining=attempts_remaining
            )
            
            if attempts_remaining > 0:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid email or password. {attempts_remaining} attempts remaining."
                )
            else:
                # Log account lockout
                security_log.log_account_lockout(
                    email=login_data.email,
                    ip_address=client_ip,
                    lockout_duration_seconds=int(login_protection.lockout_duration.total_seconds()),
                    failed_attempts=login_protection.get_failed_attempts_count(login_data.email)
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed attempts. Account locked for {login_protection.lockout_duration.total_seconds()/60} minutes."
                )
        
        # Clear failed attempts on successful login
        login_protection.clear_failed_attempts(login_data.email)
        
        # Log successful authentication
        security_log.log_auth_success(
            user_id=user.id,
            email=user.email,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        # Create tokens
        access_token = auth_service.create_access_token(user)
        refresh_token = auth_service.create_refresh_token(user)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_service.access_token_expire_minutes * 60,
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str = Field(..., description="Refresh token")


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    """
    refresh_token = request_data.refresh_token
    try:
        auth_service = AuthService(db)
        
        # Verify refresh token
        token_data = auth_service.verify_token(refresh_token)
        
        if token_data.token_type.value != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Get user
        user = await auth_service.get_user_by_id(token_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new tokens
        access_token = auth_service.create_access_token(user)
        new_refresh_token = auth_service.create_refresh_token(user)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=auth_service.access_token_expire_minutes * 60,
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/me", response_model=User, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user information.
    """
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Logout user (invalidate tokens on client side).
    """
    # In a production system, you would add tokens to a blacklist
    # For now, we'll just return a success message
    return {"message": "Successfully logged out"}


@router.get("/verify", status_code=status.HTTP_200_OK)
async def verify_token(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Verify if token is valid.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role.value
    }
