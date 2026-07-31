"""Initial complete schema

Revision ID: 001_initial_complete_schema
Revises:
Create Date: 2026-06-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid

# Timezone-aware default so stored timestamps serialize with a UTC offset -
# see app/models/user.py's _utcnow() for why a naive datetime.utcnow()
# default breaks how browsers display these timestamps.
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# revision identifiers
revision = '001_initial_complete_schema'
down_revision = None
branch_labels = None
depends_on = None

# Matches app/models/user.py's UserRole/AuthProvider Python enums exactly -
# sa.Enum(SomePyEnum) stores/compares by the member NAME ("USER", "LOCAL"),
# not its .value ("user", "local"), so the native Postgres enum types below
# must use the uppercase names to match what the ORM actually sends.
user_role_enum = sa.Enum('USER', 'ADMIN', 'SUPER_ADMIN', name='userrole')
auth_provider_enum = sa.Enum('LOCAL', 'GOOGLE', 'GITHUB', name='authprovider')


def upgrade() -> None:
    """Create all tables for FileShield application."""
    # user_role_enum/auth_provider_enum are created automatically by
    # create_table() below (SQLAlchemy emits CREATE TYPE the first time an
    # Enum-typed column is used) - no separate .create() call needed here.

    # Create users table
    op.create_table(
        'users',
        Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column('email', String(255), nullable=False, unique=True, index=True),
        Column('username', String(100), nullable=True, unique=True, index=True),
        Column('full_name', String(255), nullable=True),
        Column('hashed_password', String(255), nullable=True),
        Column('auth_provider', auth_provider_enum, nullable=False, server_default='LOCAL'),
        Column('google_id', String(255), nullable=True, unique=True),
        Column('github_id', String(255), nullable=True, unique=True),
        Column('profile_picture', String(500), nullable=True),
        Column('role', user_role_enum, nullable=False, server_default='USER'),
        Column('is_active', Boolean(), nullable=False, server_default='1'),
        Column('is_verified', Boolean(), nullable=False, server_default='0'),
        Column('created_at', DateTime(timezone=True), nullable=False, default=_utcnow),
        Column('last_login', DateTime(timezone=True), nullable=True),
    )

    # Create api_keys table
    op.create_table(
        'api_keys',
        Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column('user_id', UUID(as_uuid=True), nullable=False, index=True),
        Column('key_hash', String(255), nullable=False, unique=True),
        Column('name', String(255), nullable=False),
        Column('is_active', Boolean(), nullable=False, server_default='1'),
        Column('created_at', DateTime(timezone=True), nullable=False, default=_utcnow),
        Column('last_used', DateTime(timezone=True), nullable=True),
        Column('expires_at', DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column('user_id', UUID(as_uuid=True), nullable=True, index=True),
        Column('action', String(100), nullable=False),
        Column('resource_type', String(100), nullable=True),
        Column('resource_id', String(36), nullable=True),
        Column('ip_address', String(50), nullable=True),
        Column('user_agent', String(500), nullable=True),
        Column('details', Text(), nullable=True),
        Column('timestamp', DateTime(timezone=True), nullable=False, default=_utcnow, index=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create uploaded_files table
    op.create_table(
        'uploaded_files',
        Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column('user_id', UUID(as_uuid=True), nullable=True, index=True),
        Column('original_name', String(500), nullable=False),
        Column('stored_name', String(500), nullable=False, unique=True),
        Column('extension', String(50), nullable=True),
        Column('mime_type', String(255), nullable=True),
        Column('size_bytes', sa.BigInteger(), nullable=True),
        # Indexed, not unique - sha256 identifies file content, not an
        # upload event. Different users uploading identical bytes must get
        # independent rows (see app/models/file_record.py for the reasoning).
        Column('sha256', String(64), nullable=False, index=True),
        Column('md5', String(32), nullable=True),
        Column('sha1', String(40), nullable=True),
        Column('upload_time', DateTime(timezone=True), nullable=False, default=_utcnow),
        Column('analyzed', Boolean(), nullable=False, server_default='0'),
        Column('risk_score', Integer(), nullable=False, server_default='0'),
        Column('verdict', String(50), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Child tables (previously missing from this migration entirely - they
    # only ever existed live because database.py's create_all() added them)
    op.create_table(
        'metadata_entries',
        Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column('file_id', UUID(as_uuid=True), nullable=False, index=True),
        Column('category', String(100), nullable=False),
        Column('key', String(255), nullable=False),
        Column('value', Text(), nullable=True),
        Column('flagged', Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['file_id'], ['uploaded_files.id'], ondelete='CASCADE'),
    )
    op.create_table(
        'threat_matches',
        Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column('file_id', UUID(as_uuid=True), nullable=False, index=True),
        Column('rule_name', String(255), nullable=False),
        Column('severity', String(50), nullable=False),
        Column('description', Text(), nullable=True),
        Column('matched_data', Text(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['uploaded_files.id'], ondelete='CASCADE'),
    )
    op.create_table(
        'risk_breakdowns',
        Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column('file_id', UUID(as_uuid=True), nullable=False, index=True),
        Column('factor_name', String(255), nullable=False),
        Column('weight', Float(), nullable=False),
        Column('contribution', Integer(), nullable=False),
        Column('details', Text(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['uploaded_files.id'], ondelete='CASCADE'),
    )
    op.create_table(
        'entropy_results',
        Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        # unique=True: a file has exactly one entropy result (true 1:1)
        Column('file_id', UUID(as_uuid=True), nullable=False, unique=True, index=True),
        Column('entropy_score', Float(), nullable=False),
        Column('classification', String(50), nullable=False),
        Column('details', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['uploaded_files.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('entropy_results')
    op.drop_table('risk_breakdowns')
    op.drop_table('threat_matches')
    op.drop_table('metadata_entries')
    op.drop_table('uploaded_files')
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
    op.drop_table('users')

    bind = op.get_bind()
    auth_provider_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
