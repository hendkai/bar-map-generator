"""
SQLAlchemy ORM models for BAR Community Map Sharing Portal.
Defines User, Map, Rating, and Comment models with relationships.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean,
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from typing import Optional, List

from database import Base


class User(Base):
    """
    User model for authentication and map ownership.

    Attributes:
        id: Primary key
        username: Unique username
        email: Unique email address
        hashed_password: Bcrypt hashed password
        is_active: Whether user account is active
        created_at: Account creation timestamp
        updated_at: Last update timestamp

    Relationships:
        maps: Maps created by this user
        ratings: Ratings submitted by this user
        comments: Comments written by this user
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    maps = relationship("Map", back_populates="creator", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class Map(Base):
    """
    Map model for storing uploaded BAR maps.

    Attributes:
        id: Primary key
        name: Map display name
        shortname: Short identifier for the map
        description: Detailed map description
        author: Map author name (may differ from creator)
        version: Map version string
        creator_id: Foreign key to User who uploaded

        # BAR-specific fields
        mapx: Map width in pixels
        mapy: Map height in pixels
        maxplayers: Maximum number of players
        gravity: Gravity setting
        tidalstrength: Tidal strength setting
        maxmetal: Maximum metal available

        # Generation parameters
        size: Map size (e.g., 1024, 2048)
        terrain_type: Terrain generation type
        player_count: Number of player start positions
        noise_strength: Noise algorithm strength
        height_variation: Terrain height variation
        water_level: Water level percentage
        metal_spots: Number of metal spots
        metal_strength: Metal spot strength
        geo_spots: Number of geothermal spots
        start_positions: Start position configuration

        # File and statistics
        file_path: Path to uploaded .sd7 file
        preview_image_path: Path to preview image
        download_count: Number of times map has been downloaded
        average_rating: Cached average rating (1-5)
        rating_count: Number of ratings received

        # Metadata
        created_at: Upload timestamp
        updated_at: Last update timestamp

    Relationships:
        creator: User who uploaded the map
        ratings: Ratings for this map
        comments: Comments on this map
    """

    __tablename__ = "maps"

    id = Column(Integer, primary_key=True, index=True)

    # Basic map information
    name = Column(String(255), nullable=False, index=True)
    shortname = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(100), nullable=False)
    version = Column(String(50), default="1.0", nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # BAR-specific fields from mapinfo.txt
    mapx = Column(Integer, nullable=False)
    mapy = Column(Integer, nullable=False)
    maxplayers = Column(Integer, nullable=False)
    gravity = Column(Integer, default=100, nullable=False)
    tidalstrength = Column(Integer, default=100, nullable=False)
    maxmetal = Column(Integer, default=100, nullable=False)

    # Map generation parameters
    size = Column(Integer, nullable=False, index=True)  # e.g., 1024, 2048
    terrain_type = Column(String(50), nullable=False, index=True)  # e.g., "continental", "islands"
    player_count = Column(Integer, nullable=False, index=True)
    noise_strength = Column(Float, nullable=False)
    height_variation = Column(Float, nullable=False)
    water_level = Column(Float, nullable=False)
    metal_spots = Column(Integer, nullable=False)
    metal_strength = Column(Float, nullable=False)
    geo_spots = Column(Integer, nullable=False)
    start_positions = Column(String(50), nullable=False)  # e.g., "symmetric", "random"

    # File storage
    file_path = Column(String(500), nullable=False)  # Path to .sd7 file
    preview_image_path = Column(String(500), nullable=True)  # Path to preview image

    # Statistics
    download_count = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)
    rating_count = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="maps")
    ratings = relationship("Rating", back_populates="map", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="map", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_maps_size_terrain", "size", "terrain_type"),
        Index("ix_maps_rating", "average_rating", "rating_count"),
        Index("ix_maps_downloads", "download_count"),
    )

    def __repr__(self) -> str:
        return f"<Map(id={self.id}, name='{self.name}', terrain_type='{self.terrain_type}')>"


class Rating(Base):
    """
    Rating model for user ratings on maps.

    Attributes:
        id: Primary key
        user_id: Foreign key to User who submitted rating
        map_id: Foreign key to Map being rated
        rating: Rating value (1-5)
        created_at: Rating timestamp
        updated_at: Last update timestamp

    Relationships:
        user: User who submitted the rating
        map: Map being rated
    """

    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    map_id = Column(Integer, ForeignKey("maps.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 scale
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="ratings")
    map = relationship("Map", back_populates="ratings")

    # Ensure one rating per user per map
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_value"),
    )

    def __repr__(self) -> str:
        return f"<Rating(id={self.id}, user_id={self.user_id}, map_id={self.map_id}, rating={self.rating})>"


class Comment(Base):
    """
    Comment model for user comments on maps.

    Attributes:
        id: Primary key
        user_id: Foreign key to User who wrote comment
        map_id: Foreign key to Map being commented on
        content: Comment text content
        created_at: Comment timestamp
        updated_at: Last edit timestamp

    Relationships:
        author: User who wrote the comment
        map: Map being commented on
    """

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    map_id = Column(Integer, ForeignKey("maps.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    author = relationship("User", back_populates="comments")
    map = relationship("Map", back_populates="comments")

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, user_id={self.user_id}, map_id={self.map_id})>"
