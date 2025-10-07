"""
Evidence Pack Service.

Generates evidence packs for authorizations containing:
- Original credential/token data
- Verification results
- Audit trail
- Summary information

Evidence packs are protocol-aware (AP2 vs ACP) and packaged as ZIP files.
"""
import json
import io
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.authorization import Authorization, ProtocolType
from app.models.audit import AuditLog


class EvidencePackService:
    """Service for generating authorization evidence packs."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_evidence_pack(self, authorization_id: str) -> tuple[io.BytesIO, str]:
        """
        Generate a complete evidence pack for an authorization.
        
        Args:
            authorization_id: Authorization UUID
            
        Returns:
            Tuple of (zip_buffer, filename)
            
        Raises:
            ValueError: If authorization not found
        """
        # Fetch authorization
        result = await self.db.execute(
            select(Authorization).where(Authorization.id == authorization_id)
        )
        authorization = result.scalar_one_or_none()
        
        if not authorization:
            raise ValueError(f"Authorization {authorization_id} not found")
        
        # Fetch audit logs
        audit_logs = await self._get_audit_logs(authorization_id)
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            if authorization.protocol == ProtocolType.AP2:
                await self._add_ap2_files(zip_file, authorization, audit_logs)
            elif authorization.protocol == ProtocolType.ACP:
                await self._add_acp_files(zip_file, authorization, audit_logs)
            else:
                raise ValueError(f"Unknown protocol: {authorization.protocol}")
        
        zip_buffer.seek(0)
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"evidence_pack_{authorization.protocol}_{authorization_id[:8]}_{timestamp}.zip"
        
        return zip_buffer, filename
    
    async def _get_audit_logs(self, authorization_id: str) -> List[AuditLog]:
        """Fetch all audit logs for an authorization."""
        result = await self.db.execute(
            select(AuditLog).order_by(AuditLog.timestamp.asc())
        )
        all_logs = result.scalars().all()
        
        # Filter logs that mention this authorization_id in details
        relevant_logs = []
        for log in all_logs:
            if log.details and log.details.get('resource_id') == authorization_id:
                relevant_logs.append(log)
        
        return relevant_logs
    
    async def _add_ap2_files(
        self,
        zip_file: zipfile.ZipFile,
        authorization: Authorization,
        audit_logs: List[AuditLog]
    ):
        """Add AP2-specific files to evidence pack."""
        
        # 1. vc_jwt.txt - The JWT-VC credential
        vc_jwt = authorization.raw_payload.get('vc_jwt', '')
        zip_file.writestr('vc_jwt.txt', vc_jwt)
        
        # 2. credential.json - Structured credential data
        credential_data = {
            'vc_jwt': vc_jwt,
            'issuer_did': authorization.issuer,
            'subject_did': authorization.subject,
            'scope': authorization.scope,
            'amount_limit': str(authorization.amount_limit) if authorization.amount_limit else None,
            'expires_at': authorization.expires_at.isoformat() if authorization.expires_at else None
        }
        zip_file.writestr('credential.json', json.dumps(credential_data, indent=2))
        
        # 3. verification.json - Verification details
        verification_data = {
            'verification_status': authorization.verification_status,
            'verification_reason': authorization.verification_reason,
            'verification_details': authorization.verification_details,
            'verified_at': authorization.verified_at.isoformat() if authorization.verified_at else None,
            'current_status': authorization.status,
            'revoked_at': authorization.revoked_at.isoformat() if authorization.revoked_at else None,
            'revoke_reason': authorization.revoke_reason
        }
        zip_file.writestr('verification.json', json.dumps(verification_data, indent=2))
        
        # 4. audit.json - Audit trail
        audit_data = {
            'authorization_id': str(authorization.id),
            'protocol': 'AP2',
            'total_events': len(audit_logs),
            'events': [
                {
                    'event_id': log.id,
                    'event_type': log.event_type,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'details': log.details
                }
                for log in audit_logs
            ]
        }
        zip_file.writestr('audit.json', json.dumps(audit_data, indent=2))
        
        # 5. summary.txt - Human-readable summary
        summary = self._generate_ap2_summary(authorization, audit_logs)
        zip_file.writestr('summary.txt', summary)
    
    async def _add_acp_files(
        self,
        zip_file: zipfile.ZipFile,
        authorization: Authorization,
        audit_logs: List[AuditLog]
    ):
        """Add ACP-specific files to evidence pack."""
        
        # 1. token.json - The delegated token data
        token_data = {
            'token_id': authorization.raw_payload.get('token_id'),
            'psp_id': authorization.issuer,
            'merchant_id': authorization.subject,
            'max_amount': str(authorization.amount_limit) if authorization.amount_limit else None,
            'currency': authorization.currency,
            'expires_at': authorization.expires_at.isoformat() if authorization.expires_at else None,
            'constraints': authorization.scope,
            'raw_payload': authorization.raw_payload
        }
        zip_file.writestr('token.json', json.dumps(token_data, indent=2))
        
        # 2. verification.json - Verification details
        verification_data = {
            'verification_status': authorization.verification_status,
            'verification_reason': authorization.verification_reason,
            'verification_details': authorization.verification_details,
            'verified_at': authorization.verified_at.isoformat() if authorization.verified_at else None,
            'current_status': authorization.status,
            'revoked_at': authorization.revoked_at.isoformat() if authorization.revoked_at else None,
            'revoke_reason': authorization.revoke_reason
        }
        zip_file.writestr('verification.json', json.dumps(verification_data, indent=2))
        
        # 3. audit.json - Audit trail
        audit_data = {
            'authorization_id': str(authorization.id),
            'protocol': 'ACP',
            'token_id': authorization.raw_payload.get('token_id'),
            'total_events': len(audit_logs),
            'events': [
                {
                    'event_id': log.id,
                    'event_type': log.event_type,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'details': log.details
                }
                for log in audit_logs
            ]
        }
        zip_file.writestr('audit.json', json.dumps(audit_data, indent=2))
        
        # 4. summary.txt - Human-readable summary
        summary = self._generate_acp_summary(authorization, audit_logs)
        zip_file.writestr('summary.txt', summary)
    
    def _generate_ap2_summary(self, authorization: Authorization, audit_logs: List[AuditLog]) -> str:
        """Generate human-readable summary for AP2 authorization."""
        lines = [
            "=" * 80,
            "AUTHORIZATION EVIDENCE PACK - AP2 (JWT-VC)",
            "=" * 80,
            "",
            "AUTHORIZATION DETAILS",
            "-" * 80,
            f"Authorization ID:  {authorization.id}",
            f"Protocol:          AP2 (JWT-VC)",
            f"Issuer DID:        {authorization.issuer}",
            f"Subject DID:       {authorization.subject}",
            f"Scope:             {authorization.scope.get('scope') if authorization.scope else 'N/A'}",
            f"Amount Limit:      {authorization.amount_limit or 'N/A'}",
            f"Expires At:        {authorization.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC') if authorization.expires_at else 'N/A'}",
            f"Current Status:    {authorization.status}",
            "",
            "VERIFICATION INFORMATION",
            "-" * 80,
            f"Verification Status:  {authorization.verification_status or 'Not Verified'}",
            f"Verification Reason:  {authorization.verification_reason or 'N/A'}",
            f"Verified At:          {authorization.verified_at.strftime('%Y-%m-%d %H:%M:%S UTC') if authorization.verified_at else 'N/A'}",
            "",
        ]
        
        if authorization.revoked_at:
            lines.extend([
                "REVOCATION INFORMATION",
                "-" * 80,
                f"Revoked At:  {authorization.revoked_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"Reason:      {authorization.revoke_reason or 'N/A'}",
                "",
            ])
        
        lines.extend([
            "AUDIT TRAIL",
            "-" * 80,
            f"Total Events:  {len(audit_logs)}",
            ""
        ])
        
        for i, log in enumerate(audit_logs, 1):
            timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if log.timestamp else 'N/A'
            lines.append(f"{i}. [{timestamp}] {log.event_type}")
        
        lines.extend([
            "",
            "TIMESTAMPS",
            "-" * 80,
            f"Created:  {authorization.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if authorization.created_at else 'N/A'}",
            f"Updated:  {authorization.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if authorization.updated_at else 'N/A'}",
            "",
            "=" * 80,
            f"Evidence pack generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "=" * 80,
        ])
        
        return "\n".join(lines)
    
    def _generate_acp_summary(self, authorization: Authorization, audit_logs: List[AuditLog]) -> str:
        """Generate human-readable summary for ACP authorization."""
        lines = [
            "=" * 80,
            "AUTHORIZATION EVIDENCE PACK - ACP (Delegated Token)",
            "=" * 80,
            "",
            "AUTHORIZATION DETAILS",
            "-" * 80,
            f"Authorization ID:  {authorization.id}",
            f"Protocol:          ACP (Authorization Credential Protocol)",
            f"Token ID:          {authorization.raw_payload.get('token_id', 'N/A')}",
            f"PSP ID:            {authorization.issuer}",
            f"Merchant ID:       {authorization.subject}",
            f"Max Amount:        {authorization.amount_limit or 'N/A'}",
            f"Currency:          {authorization.currency or 'N/A'}",
            f"Expires At:        {authorization.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC') if authorization.expires_at else 'N/A'}",
            f"Current Status:    {authorization.status}",
            "",
        ]
        
        if authorization.scope:
            lines.extend([
                "CONSTRAINTS",
                "-" * 80,
            ])
            constraints = authorization.scope.get('constraints', {}) if isinstance(authorization.scope, dict) else {}
            if constraints:
                for key, value in constraints.items():
                    lines.append(f"{key.capitalize():15} {value}")
            else:
                lines.append("No constraints defined")
            lines.append("")
        
        lines.extend([
            "VERIFICATION INFORMATION",
            "-" * 80,
            f"Verification Status:  {authorization.verification_status or 'Not Verified'}",
            f"Verification Reason:  {authorization.verification_reason or 'N/A'}",
            f"Verified At:          {authorization.verified_at.strftime('%Y-%m-%d %H:%M:%S UTC') if authorization.verified_at else 'N/A'}",
            "",
        ])
        
        if authorization.revoked_at:
            lines.extend([
                "REVOCATION INFORMATION",
                "-" * 80,
                f"Revoked At:  {authorization.revoked_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"Reason:      {authorization.revoke_reason or 'N/A'}",
                "",
            ])
        
        lines.extend([
            "AUDIT TRAIL",
            "-" * 80,
            f"Total Events:  {len(audit_logs)}",
            ""
        ])
        
        for i, log in enumerate(audit_logs, 1):
            timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if log.timestamp else 'N/A'
            lines.append(f"{i}. [{timestamp}] {log.event_type}")
        
        lines.extend([
            "",
            "TIMESTAMPS",
            "-" * 80,
            f"Created:  {authorization.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if authorization.created_at else 'N/A'}",
            f"Updated:  {authorization.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if authorization.updated_at else 'N/A'}",
            "",
            "=" * 80,
            f"Evidence pack generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "=" * 80,
        ])
        
        return "\n".join(lines)


