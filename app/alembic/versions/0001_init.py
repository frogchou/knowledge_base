from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.mysql as mysql
import uuid

revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        'knowledge_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('source_type', sa.Enum('text', 'url', 'file', name='sourcetype'), nullable=False),
        sa.Column('source_url', sa.String(500)),
        sa.Column('original_filename', sa.String(255)),
        sa.Column('file_path', sa.String(500)),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('content_text', mysql.LONGTEXT(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False, index=True),
        sa.Column('summary', sa.Text()),
        sa.Column('keywords', sa.JSON()),
        sa.Column('tags', sa.JSON()),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_owner', 'knowledge_items', ['owner_id'])
    op.create_index('idx_created', 'knowledge_items', ['created_at'])
    op.create_index('idx_updated', 'knowledge_items', ['updated_at'])
    op.create_index('idx_source_type', 'knowledge_items', ['source_type'])


def downgrade():
    op.drop_table('knowledge_items')
    op.drop_table('users')
