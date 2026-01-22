"""Initial migration

Create initial database schema for BAR Community Map Sharing Portal.
Includes tables for users, maps, ratings, and comments.

Revision ID: 001
Revises:
Create Date: 2026-01-21 20:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import CheckConstraint


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'])
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create maps table
    op.create_table(
        'maps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('shortname', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('author', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('mapx', sa.Integer(), nullable=False),
        sa.Column('mapy', sa.Integer(), nullable=False),
        sa.Column('maxplayers', sa.Integer(), nullable=False),
        sa.Column('gravity', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('tidalstrength', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('maxmetal', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('terrain_type', sa.String(length=50), nullable=False),
        sa.Column('player_count', sa.Integer(), nullable=False),
        sa.Column('noise_strength', sa.Float(), nullable=False),
        sa.Column('height_variation', sa.Float(), nullable=False),
        sa.Column('water_level', sa.Float(), nullable=False),
        sa.Column('metal_spots', sa.Integer(), nullable=False),
        sa.Column('metal_strength', sa.Float(), nullable=False),
        sa.Column('geo_spots', sa.Integer(), nullable=False),
        sa.Column('start_positions', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('preview_image_path', sa.String(length=500), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_rating', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('rating_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('average_rating >= 0 AND average_rating <= 5', name='ck_average_rating_range')
    )
    op.create_index(op.f('ix_maps_id'), 'maps', ['id'])
    op.create_index(op.f('ix_maps_name'), 'maps', ['name'])
    op.create_index(op.f('ix_maps_size'), 'maps', ['size'])
    op.create_index(op.f('ix_maps_terrain_type'), 'maps', ['terrain_type'])
    op.create_index(op.f('ix_maps_player_count'), 'maps', ['player_count'])
    op.create_index(op.f('ix_maps_size_terrain'), 'maps', ['size', 'terrain_type'])
    op.create_index(op.f('ix_maps_rating'), 'maps', ['average_rating', 'rating_count'])
    op.create_index(op.f('ix_maps_downloads'), 'maps', ['download_count'])

    # Create ratings table
    op.create_table(
        'ratings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('map_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='ck_rating_value')
    )
    op.create_index(op.f('ix_ratings_id'), 'ratings', ['id'])

    # Create comments table
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('map_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comments_id'), 'comments', ['id'])


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_index(op.f('ix_comments_id'), table_name='comments')
    op.drop_table('comments')

    op.drop_index(op.f('ix_ratings_id'), table_name='ratings')
    op.drop_table('ratings')

    op.drop_index(op.f('ix_maps_downloads'), table_name='maps')
    op.drop_index(op.f('ix_maps_rating'), table_name='maps')
    op.drop_index(op.f('ix_maps_size_terrain'), table_name='maps')
    op.drop_index(op.f('ix_maps_player_count'), table_name='maps')
    op.drop_index(op.f('ix_maps_terrain_type'), table_name='maps')
    op.drop_index(op.f('ix_maps_size'), table_name='maps')
    op.drop_index(op.f('ix_maps_name'), table_name='maps')
    op.drop_index(op.f('ix_maps_id'), table_name='maps')
    op.drop_table('maps')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
