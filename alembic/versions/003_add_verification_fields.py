"""Add verification fields to mandates table

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add verification fields to mandates table
    op.add_column('mandates', sa.Column('verification_status', sa.String(length=50), nullable=True))
    op.add_column('mandates', sa.Column('verification_reason', sa.Text(), nullable=True))
    op.add_column('mandates', sa.Column('verification_details', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('mandates', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes for verification fields
    op.create_index(op.f('ix_mandates_verification_status'), 'mandates', ['verification_status'], unique=False)
    op.create_index(op.f('ix_mandates_verified_at'), 'mandates', ['verified_at'], unique=False)
    
    # Set default verification status for existing records
    op.execute("UPDATE mandates SET verification_status = 'PENDING' WHERE verification_status IS NULL")


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_mandates_verified_at'), table_name='mandates')
    op.drop_index(op.f('ix_mandates_verification_status'), table_name='mandates')
    
    # Drop verification columns
    op.drop_column('mandates', 'verified_at')
    op.drop_column('mandates', 'verification_details')
    op.drop_column('mandates', 'verification_reason')
    op.drop_column('mandates', 'verification_status')


