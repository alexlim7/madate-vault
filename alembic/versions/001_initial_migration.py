"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create mandates table
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
    op.create_index(op.f('ix_mandates_expires_at'), 'mandates', ['expires_at'], unique=False)
    op.create_index(op.f('ix_mandates_id'), 'mandates', ['id'], unique=False)
    op.create_index(op.f('ix_mandates_issuer_did'), 'mandates', ['issuer_did'], unique=False)
    op.create_index(op.f('ix_mandates_mandate_id'), 'mandates', ['mandate_id'], unique=True)
    op.create_index(op.f('ix_mandates_status'), 'mandates', ['status'], unique=False)

    # Create audit_events table
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
    op.create_index(op.f('ix_audit_events_id'), 'audit_events', ['id'], unique=False)
    op.create_index(op.f('ix_audit_events_mandate_id'), 'audit_events', ['mandate_id'], unique=False)
    op.create_index(op.f('ix_audit_events_event_type'), 'audit_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_events_user_id'), 'audit_events', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_events_user_id'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_event_type'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_mandate_id'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_id'), table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_index(op.f('ix_mandates_status'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_mandate_id'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_issuer_did'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_id'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_expires_at'), table_name='mandates')
    op.drop_table('mandates')


