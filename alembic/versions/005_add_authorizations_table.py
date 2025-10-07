"""Add authorizations table for multi-protocol support

Revision ID: 005
Revises: 004
Create Date: 2025-10-01 00:00:00.000000

This migration introduces a protocol-agnostic authorizations table
and migrates existing AP2 data from the mandates table.

Changes:
- Creates authorizations table with protocol support
- Backfills data from mandates table (AP2 protocol)
- Creates mandate_view for backward compatibility
- Adds indexes for performance
- Marks mandates table as deprecated (kept for compatibility)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade database schema.
    
    Steps:
    1. Create authorizations table
    2. Add indexes
    3. Backfill data from mandates table
    4. Create compatibility view
    """
    
    # Step 1: Create authorizations table
    op.execute("""
        CREATE TABLE authorizations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            
            -- Protocol identification
            protocol TEXT NOT NULL CHECK (protocol IN ('AP2', 'ACP')),
            
            -- Core fields (protocol-agnostic)
            issuer TEXT NOT NULL,  -- AP2: issuer_did, ACP: psp_id
            subject TEXT NOT NULL,  -- AP2: subject_did, ACP: merchant_id
            scope JSONB,  -- AP2: scope string, ACP: constraints object
            amount_limit NUMERIC(18,2),  -- AP2: amount_limit, ACP: max_amount
            currency TEXT,  -- ACP required, AP2 optional (extracted from amount_limit)
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('VALID', 'EXPIRED', 'REVOKED', 'ACTIVE')),
            
            -- Protocol-specific data
            raw_payload JSONB NOT NULL,  -- Complete credential (AP2: decoded JWT, ACP: full JSON)
            
            -- Multi-tenancy
            tenant_id TEXT NOT NULL,
            
            -- Verification metadata
            verification_status TEXT,
            verification_reason TEXT,
            verification_details JSONB,
            verified_at TIMESTAMP WITH TIME ZONE,
            
            -- Retention & lifecycle
            retention_days INTEGER DEFAULT 90,
            deleted_at TIMESTAMP WITH TIME ZONE,
            revoked_at TIMESTAMP WITH TIME ZONE,
            revoke_reason TEXT,
            
            -- Audit metadata
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            created_by TEXT,  -- User ID who created
            
            -- Foreign keys
            FOREIGN KEY (tenant_id) REFERENCES customers(tenant_id)
        )
    """)
    
    # Step 2: Create indexes for performance
    op.create_index('ix_authorizations_id', 'authorizations', ['id'])
    op.create_index('ix_authorizations_protocol', 'authorizations', ['protocol'])
    op.create_index('ix_authorizations_status', 'authorizations', ['status'])
    op.create_index('ix_authorizations_expires_at', 'authorizations', ['expires_at'])
    op.create_index('ix_authorizations_tenant_id', 'authorizations', ['tenant_id'])
    op.create_index('ix_authorizations_issuer', 'authorizations', ['issuer'])
    op.create_index('ix_authorizations_subject', 'authorizations', ['subject'])
    op.create_index('ix_authorizations_deleted_at', 'authorizations', ['deleted_at'])
    
    # Composite indexes for common queries
    op.create_index(
        'ix_authorizations_tenant_protocol',
        'authorizations',
        ['tenant_id', 'protocol']
    )
    op.create_index(
        'ix_authorizations_tenant_status',
        'authorizations',
        ['tenant_id', 'status']
    )
    
    # Step 3: Backfill data from mandates table
    op.execute("""
        INSERT INTO authorizations (
            id,
            protocol,
            issuer,
            subject,
            scope,
            amount_limit,
            currency,
            expires_at,
            status,
            raw_payload,
            tenant_id,
            verification_status,
            verification_reason,
            verification_details,
            verified_at,
            retention_days,
            deleted_at,
            created_at,
            updated_at
        )
        SELECT
            -- Use existing mandate ID (convert to UUID if needed)
            CAST(id AS UUID),
            
            -- All existing mandates are AP2 protocol
            'AP2' AS protocol,
            
            -- Map fields
            issuer_did AS issuer,
            COALESCE(subject_did, 'unknown') AS subject,
            
            -- Convert scope to JSONB
            CASE 
                WHEN scope IS NOT NULL THEN jsonb_build_object('scope', scope)
                ELSE NULL
            END AS scope,
            
            -- Parse amount_limit (extract numeric value)
            CASE
                WHEN amount_limit IS NOT NULL THEN
                    CAST(regexp_replace(amount_limit, '[^0-9.]', '', 'g') AS NUMERIC(18,2))
                ELSE NULL
            END AS amount_limit,
            
            -- Extract currency from amount_limit (e.g., "5000.00 USD" -> "USD")
            CASE
                WHEN amount_limit IS NOT NULL THEN
                    TRIM(regexp_replace(amount_limit, '[0-9.,]', '', 'g'))
                ELSE NULL
            END AS currency,
            
            -- Expires at (required, use far future if NULL)
            COALESCE(expires_at, TIMESTAMP '2099-12-31 23:59:59') AS expires_at,
            
            -- Map status (normalize)
            UPPER(COALESCE(status, 'ACTIVE')) AS status,
            
            -- Raw payload: decode JWT and store as JSONB
            jsonb_build_object(
                'vc_jwt', vc_jwt,
                'issuer_did', issuer_did,
                'subject_did', subject_did,
                'scope', scope,
                'amount_limit', amount_limit,
                'original_format', 'jwt-vc'
            ) AS raw_payload,
            
            -- Tenant
            tenant_id,
            
            -- Verification
            verification_status,
            verification_reason,
            COALESCE(verification_details, '{}'::jsonb) AS verification_details,
            verified_at,
            
            -- Retention
            COALESCE(retention_days, 90) AS retention_days,
            deleted_at,
            
            -- Timestamps
            created_at,
            updated_at
        FROM mandates
        WHERE deleted_at IS NULL  -- Only migrate active/non-deleted mandates
    """)
    
    # Step 4: Create compatibility view for backward compatibility
    op.execute("""
        CREATE VIEW mandate_view AS
        SELECT
            -- Map authorizations back to mandate format
            CAST(id AS TEXT) AS id,
            (raw_payload->>'vc_jwt') AS vc_jwt,
            issuer AS issuer_did,
            subject AS subject_did,
            (scope->>'scope') AS scope,
            CASE
                WHEN amount_limit IS NOT NULL AND currency IS NOT NULL THEN
                    amount_limit::TEXT || ' ' || currency
                WHEN amount_limit IS NOT NULL THEN
                    amount_limit::TEXT
                ELSE NULL
            END AS amount_limit,
            expires_at,
            LOWER(status) AS status,
            retention_days,
            deleted_at,
            tenant_id,
            verification_status,
            verification_reason,
            verification_details,
            verified_at,
            created_at,
            updated_at,
            protocol  -- Additional field showing protocol type
        FROM authorizations
        WHERE protocol = 'AP2'  -- View only shows AP2 mandates
    """)
    
    # Step 5: Add comments to mark mandates table as deprecated
    op.execute("""
        COMMENT ON TABLE mandates IS 
        'DEPRECATED: Legacy table for AP2 mandates only. 
         Use authorizations table for new data. 
         This table is kept for backward compatibility and will be removed in v2.0.
         Migration date: 2025-10-01'
    """)
    
    # Step 6: Add trigger to keep updated_at current
    op.execute("""
        CREATE OR REPLACE FUNCTION update_authorizations_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER authorizations_updated_at
            BEFORE UPDATE ON authorizations
            FOR EACH ROW
            EXECUTE FUNCTION update_authorizations_updated_at();
    """)
    
    print("✓ Created authorizations table")
    print("✓ Created indexes")
    print("✓ Backfilled data from mandates table")
    print("✓ Created mandate_view for compatibility")
    print("✓ Marked mandates table as deprecated")


def downgrade() -> None:
    """
    Downgrade database schema.
    
    Warning: This will drop the authorizations table and all ACP data!
    AP2 data will remain in the mandates table.
    """
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS authorizations_updated_at ON authorizations")
    op.execute("DROP FUNCTION IF EXISTS update_authorizations_updated_at()")
    
    # Drop view
    op.execute("DROP VIEW IF EXISTS mandate_view")
    
    # Remove comment from mandates table
    op.execute("COMMENT ON TABLE mandates IS NULL")
    
    # Drop indexes (will be dropped with table, but explicit for clarity)
    op.drop_index('ix_authorizations_tenant_status', 'authorizations')
    op.drop_index('ix_authorizations_tenant_protocol', 'authorizations')
    op.drop_index('ix_authorizations_deleted_at', 'authorizations')
    op.drop_index('ix_authorizations_subject', 'authorizations')
    op.drop_index('ix_authorizations_issuer', 'authorizations')
    op.drop_index('ix_authorizations_tenant_id', 'authorizations')
    op.drop_index('ix_authorizations_expires_at', 'authorizations')
    op.drop_index('ix_authorizations_status', 'authorizations')
    op.drop_index('ix_authorizations_protocol', 'authorizations')
    op.drop_index('ix_authorizations_id', 'authorizations')
    
    # Drop authorizations table
    op.drop_table('authorizations')
    
    print("✓ Dropped authorizations table")
    print("✓ Restored mandates table as primary")
    print("⚠️  Warning: Any ACP authorizations created have been lost!")


