"""
User management API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_active_user, User as AuthUser, UserRole
from app.core.rate_limiting import create_endpoint_rate_limit
from app.schemas.user import (
    UserRegister, UserResponse, UserUpdate, UserListResponse,
    UserChangePassword, UserResetPasswordRequest, UserResetPassword,
    UserInvite, UserAcceptInvite, InvitationResponse
)
from app.services.user_service import UserService
from app.models.user import UserRole as ModelUserRole, UserStatus

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=http_status.HTTP_201_CREATED)
@create_endpoint_rate_limit("users", "create")
async def register_user(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Register a new user account.
    
    This endpoint allows self-registration for new users.
    For the first user in a tenant, use auto_verify=True.
    """
    try:
        user_service = UserService(db)
        
        # Create user
        user = await user_service.create_user(
            email=user_data.email,
            password=user_data.password,
            tenant_id=user_data.tenant_id,
            role=user_data.role or ModelUserRole.CUSTOMER_USER,
            full_name=user_data.full_name,
            phone=user_data.phone,
            auto_verify=False  # Email verification required
        )
        
        return UserResponse.model_validate(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )


@router.post("/invite", response_model=InvitationResponse, status_code=http_status.HTTP_201_CREATED)
@create_endpoint_rate_limit("users", "create")
async def invite_user(
    invite_data: UserInvite,
    request: Request,
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> InvitationResponse:
    """
    Invite a new user to the platform.
    
    Only admins and customer_admins can invite users.
    The invited user will receive an email with an invitation link.
    """
    # Check if current user has permission to invite
    if current_user.role not in [UserRole.ADMIN, UserRole.CUSTOMER_ADMIN]:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only admins can invite users"
        )
    
    # Non-admin users can only invite to their own tenant
    if current_user.role != UserRole.ADMIN and invite_data.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Cannot invite users to other tenants"
        )
    
    try:
        user_service = UserService(db)
        
        user, invitation_token = await user_service.invite_user(
            email=invite_data.email,
            tenant_id=invite_data.tenant_id,
            role=invite_data.role,
            invited_by_user_id=current_user.id,
            full_name=invite_data.full_name
        )
        
        return InvitationResponse(
            message=f"Invitation sent to {invite_data.email}",
            invitation_token=invitation_token,
            expires_at=user.invitation_expires,
            user=UserResponse.model_validate(user)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invite user: {str(e)}"
        )


@router.post("/accept-invite", response_model=UserResponse)
@create_endpoint_rate_limit("users", "create")
async def accept_invite(
    accept_data: UserAcceptInvite,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Accept a user invitation and activate account.
    
    The user must provide the invitation token received via email
    and set their password.
    """
    try:
        user_service = UserService(db)
        
        user = await user_service.accept_invitation(
            invitation_token=accept_data.invitation_token,
            password=accept_data.password,
            full_name=accept_data.full_name,
            phone=accept_data.phone
        )
        
        return UserResponse.model_validate(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept invitation: {str(e)}"
        )


@router.get("/", response_model=UserListResponse)
@create_endpoint_rate_limit("users", "list")
async def list_users(
    request: Request,
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    role: Optional[ModelUserRole] = Query(None, description="Filter by role"),
    status: Optional[UserStatus] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserListResponse:
    """
    List users with optional filtering.
    
    Admins can see all users.
    Customer admins can only see users in their tenant.
    Regular users can only see themselves.
    """
    try:
        user_service = UserService(db)
        
        # Enforce tenant isolation for non-admins
        if current_user.role != UserRole.ADMIN:
            tenant_id = current_user.tenant_id
        
        # Regular users can only see themselves
        if current_user.role == UserRole.CUSTOMER_USER:
            result = await user_service.get_user_by_id(current_user.id)
            if result:
                users = [result]
                total = 1
            else:
                users = []
                total = 0
            
            return UserListResponse(
                users=[UserResponse.model_validate(u) for u in users],
                total=total,
                limit=limit,
                offset=offset
            )
        
        result = await user_service.list_users(
            tenant_id=tenant_id,
            role=role,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return UserListResponse(
            users=[UserResponse.model_validate(u) for u in result["users"]],
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserResponse)
@create_endpoint_rate_limit("users", "get")
async def get_user(
    user_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get user by ID.
    
    Users can only view their own profile unless they are admins.
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        # Check permissions
        if current_user.role != UserRole.ADMIN:
            if user.id != current_user.id:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own profile"
                )
            if user.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=http_status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this tenant"
                )
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.patch("/{user_id}", response_model=UserResponse)
@create_endpoint_rate_limit("users", "update")
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    request: Request,
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update user information.
    
    Users can update their own profile.
    Admins can update any user.
    Only admins can change roles and status.
    """
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        # Check permissions
        is_admin = current_user.role == UserRole.ADMIN
        is_self = user.id == current_user.id
        
        if not is_admin and not is_self:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You can only update your own profile"
            )
        
        # Only admins can change role and status
        if not is_admin and (update_data.role is not None or update_data.status is not None):
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only admins can change user roles and status"
            )
        
        updated_user = await user_service.update_user(
            user_id=user_id,
            full_name=update_data.full_name,
            phone=update_data.phone,
            role=update_data.role,
            status=update_data.status
        )
        
        return UserResponse.model_validate(updated_user)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.post("/{user_id}/change-password", response_model=UserResponse)
@create_endpoint_rate_limit("users", "update")
async def change_password(
    user_id: str,
    password_data: UserChangePassword,
    request: Request,
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Change user password.
    
    Users can only change their own password.
    """
    # Users can only change their own password
    if user_id != current_user.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="You can only change your own password"
        )
    
    try:
        user_service = UserService(db)
        
        user = await user_service.change_password(
            user_id=user_id,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        return UserResponse.model_validate(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )


@router.post("/reset-password-request")
@create_endpoint_rate_limit("users", "update")
async def request_password_reset(
    reset_request: UserResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset.
    
    Sends a password reset email to the user if the email exists.
    Returns success regardless to avoid email enumeration.
    """
    try:
        user_service = UserService(db)
        await user_service.request_password_reset(reset_request.email)
        
        return {
            "message": "If this email exists, a password reset link has been sent"
        }
        
    except Exception:
        # Always return success to avoid email enumeration
        return {
            "message": "If this email exists, a password reset link has been sent"
        }


@router.post("/reset-password", response_model=UserResponse)
@create_endpoint_rate_limit("users", "update")
async def reset_password(
    reset_data: UserResetPassword,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Reset password using reset token.
    
    The user must provide the reset token received via email.
    """
    try:
        user_service = UserService(db)
        
        user = await user_service.reset_password(
            reset_token=reset_data.reset_token,
            new_password=reset_data.new_password
        )
        
        return UserResponse.model_validate(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )


@router.delete("/{user_id}", status_code=http_status.HTTP_204_NO_CONTENT)
@create_endpoint_rate_limit("users", "delete")
async def delete_user(
    user_id: str,
    request: Request,
    current_user: AuthUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a user.
    
    Only admins can delete users.
    Users cannot delete themselves.
    """
    # Only admins can delete users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself"
        )
    
    try:
        user_service = UserService(db)
        await user_service.delete_user(user_id)
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

