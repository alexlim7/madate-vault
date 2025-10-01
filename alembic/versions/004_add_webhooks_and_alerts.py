"""Add webhooks and alerts tables

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhooks table
    op.create_table('webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('events', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['customers.tenant_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhooks_id'), 'webhooks', ['id'], unique=False)
    op.create_index(op.f('ix_webhooks_tenant_id'), 'webhooks', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_webhooks_is_active'), 'webhooks', ['is_active'], unique=False)

    # Create webhook_deliveries table
    op.create_table('webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('webhook_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mandate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_delivered', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandates.id'], ),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_deliveries_id'), 'webhook_deliveries', ['id'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_webhook_id'), 'webhook_deliveries', ['webhook_id'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_mandate_id'), 'webhook_deliveries', ['mandate_id'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_event_type'), 'webhook_deliveries', ['event_type'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_delivered_at'), 'webhook_deliveries', ['delivered_at'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_next_retry_at'), 'webhook_deliveries', ['next_retry_at'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_is_delivered'), 'webhook_deliveries', ['is_delivered'], unique=False)

    # Create alerts table
    op.create_table('alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mandate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alert_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandates.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['customers.tenant_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)
    op.create_index(op.f('ix_alerts_tenant_id'), 'alerts', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_alerts_mandate_id'), 'alerts', ['mandate_id'], unique=False)
    op.create_index(op.f('ix_alerts_alert_type'), 'alerts', ['alert_type'], unique=False)
    op.create_index(op.f('ix_alerts_severity'), 'alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_alerts_is_read'), 'alerts', ['is_read'], unique=False)
    op.create_index(op.f('ix_alerts_is_resolved'), 'alerts', ['is_resolved'], unique=False)


def downgrade() -> None:
    # Drop alerts table
    op.drop_index(op.f('ix_alerts_is_resolved'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_is_read'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_severity'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_alert_type'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_mandate_id'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_tenant_id'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_id'), table_name='alerts')
    op.drop_table('alerts')

    # Drop webhook_deliveries table
    op.drop_index(op.f('ix_webhook_deliveries_is_delivered'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_next_retry_at'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_delivered_at'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_event_type'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_mandate_id'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_webhook_id'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_id'), table_name='webhook_deliveries')
    op.drop_table('webhook_deliveries')

    # Drop webhooks table
    op.drop_index(op.f('ix_webhooks_is_active'), table_name='webhooks')
    op.drop_index(op.f('ix_webhooks_tenant_id'), table_name='webhooks')
    op.drop_index(op.f('ix_webhooks_id'), table_name='webhooks')
    op.drop_table('webhooks')


