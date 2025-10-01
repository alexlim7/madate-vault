"""Update schema with new requirements

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old tables
    op.drop_table('audit_events')
    op.drop_table('mandates')
    
    # Create customers table for multi-tenancy
    op.create_table('customers',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('tenant_id')
    )
    op.create_index(op.f('ix_customers_tenant_id'), 'customers', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_customers_email'), 'customers', ['email'], unique=False)
    
    # Create mandates table with new schema
    op.create_table('mandates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vc_jwt', sa.Text(), nullable=False),
        sa.Column('issuer_did', sa.String(length=255), nullable=False),
        sa.Column('subject_did', sa.String(length=255), nullable=True),
        sa.Column('scope', sa.String(length=255), nullable=True),
        sa.Column('amount_limit', sa.String(length=50), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('retention_days', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['customers.tenant_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mandates_id'), 'mandates', ['id'], unique=False)
    op.create_index(op.f('ix_mandates_issuer_did'), 'mandates', ['issuer_did'], unique=False)
    op.create_index(op.f('ix_mandates_expires_at'), 'mandates', ['expires_at'], unique=False)
    op.create_index(op.f('ix_mandates_status'), 'mandates', ['status'], unique=False)
    op.create_index(op.f('ix_mandates_deleted_at'), 'mandates', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_mandates_tenant_id'), 'mandates', ['tenant_id'], unique=False)
    
    # Create audit_log table with new schema
    op.create_table('audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mandate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_id'), 'audit_log', ['id'], unique=False)
    op.create_index(op.f('ix_audit_log_mandate_id'), 'audit_log', ['mandate_id'], unique=False)
    op.create_index(op.f('ix_audit_log_event_type'), 'audit_log', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_log_timestamp'), 'audit_log', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop new tables
    op.drop_index(op.f('ix_audit_log_timestamp'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_event_type'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_mandate_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_id'), table_name='audit_log')
    op.drop_table('audit_log')
    
    op.drop_index(op.f('ix_mandates_tenant_id'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_deleted_at'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_status'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_expires_at'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_issuer_did'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_id'), table_name='mandates')
    op.drop_table('mandates')
    
    op.drop_index(op.f('ix_customers_email'), table_name='customers')
    op.drop_index(op.f('ix_customers_tenant_id'), table_name='customers')
    op.drop_table('customers')
    
    # Recreate old tables (simplified version)
    op.create_table('mandates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mandate_id', sa.String(length=255), nullable=False),
        sa.Column('issuer_did', sa.String(length=255), nullable=False),
        sa.Column('subject_did', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('credential_type', sa.String(length=255), nullable=True),
        sa.Column('credential_subject', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verification_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_jwt', sa.Text(), nullable=False),
        sa.Column('parsed_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mandates_status'), 'mandates', ['status'], unique=False)
    op.create_index(op.f('ix_mandates_mandate_id'), 'mandates', ['mandate_id'], unique=True)
    op.create_index(op.f('ix_mandates_issuer_did'), 'mandates', ['issuer_did'], unique=False)
    op.create_index(op.f('ix_mandates_id'), 'mandates', ['id'], unique=False)
    op.create_index(op.f('ix_mandates_expires_at'), 'mandates', ['expires_at'], unique=False)
    
    op.create_table('audit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mandate_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_description', sa.Text(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('event_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandates.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_events_user_id'), 'audit_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_events_event_type'), 'audit_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_events_mandate_id'), 'audit_events', ['mandate_id'], unique=False)
    op.create_index(op.f('ix_audit_events_id'), 'audit_events', ['id'], unique=False)


