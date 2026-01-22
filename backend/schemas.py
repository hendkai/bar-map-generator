"""
Pydantic schemas for API request/response validation.
Defines schemas for User, Map, Rating, and Comment models.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 characters)"
    )

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Validate username contains only alphanumeric characters and underscores."""
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must contain only alphanumeric characters and underscores')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserProfile(BaseModel):
    """Minimal user profile schema for nested responses."""
    id: int
    username: str

    class Config:
        """Pydantic configuration."""
        from_attributes = True


# =============================================================================
# Map Schemas
# =============================================================================

class MapGenerationParams(BaseModel):
    """Schema for map generation parameters."""
    size: int = Field(..., ge=512, le=4096, description="Map size in pixels")
    terrain_type: str = Field(
        ...,
        description="Terrain type (continental, islands, mountainous, etc.)"
    )
    player_count: int = Field(..., ge=1, le=32, description="Number of players")
    noise_strength: float = Field(..., ge=0.0, le=10.0, description="Noise strength")
    height_variation: float = Field(..., ge=0.0, le=1.0, description="Height variation")
    water_level: float = Field(..., ge=0.0, le=1.0, description="Water level percentage")
    metal_spots: int = Field(..., ge=0, description="Number of metal spots")
    metal_strength: float = Field(..., ge=0.0, le=10.0, description="Metal spot strength")
    geo_spots: int = Field(..., ge=0, description="Number of geothermal spots")
    start_positions: str = Field(..., description="Start position configuration")


class BARMapInfo(BaseModel):
    """Schema for BAR-specific map information from mapinfo.txt."""
    mapx: int = Field(..., ge=1, description="Map width in pixels")
    mapy: int = Field(..., ge=1, description="Map height in pixels")
    maxplayers: int = Field(..., ge=1, le=32, description="Maximum players")
    gravity: int = Field(default=100, ge=0, description="Gravity setting")
    tidalstrength: int = Field(default=100, ge=0, description="Tidal strength setting")
    maxmetal: int = Field(default=100, ge=0, description="Maximum metal available")


class MapBase(BaseModel):
    """Base map schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Map display name")
    shortname: str = Field(..., min_length=1, max_length=100, description="Short identifier")
    description: Optional[str] = Field(None, description="Detailed map description")
    author: str = Field(..., min_length=1, max_length=100, description="Map author")
    version: str = Field(default="1.0", max_length=50, description="Map version")


class MapCreate(MapBase):
    """Schema for map creation/upload."""
    generation_params: MapGenerationParams = Field(
        ...,
        description="Map generation parameters"
    )
    bar_info: BARMapInfo = Field(
        ...,
        description="BAR-specific map information"
    )

    # File info will be handled separately via UploadFile
    # This schema validates the metadata that accompanies the upload


class MapUpdate(BaseModel):
    """Schema for map update."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    version: Optional[str] = Field(None, max_length=50)


class MapResponse(MapBase):
    """Schema for map response."""
    id: int
    creator_id: int
    creator: UserProfile

    # BAR-specific fields
    mapx: int
    mapy: int
    maxplayers: int
    gravity: int
    tidalstrength: int
    maxmetal: int

    # Generation parameters
    size: int
    terrain_type: str
    player_count: int
    noise_strength: float
    height_variation: float
    water_level: float
    metal_spots: int
    metal_strength: float
    geo_spots: int
    start_positions: str

    # Statistics
    download_count: int
    average_rating: float
    rating_count: int

    # File paths (relative to upload directory)
    file_path: str
    preview_image_path: Optional[str] = None

    # Metadata
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class MapListItem(BaseModel):
    """Simplified map schema for list views (better performance)."""
    id: int
    name: str
    shortname: str
    author: str
    terrain_type: str
    size: int
    player_count: int
    maxplayers: int
    average_rating: float
    rating_count: int
    download_count: int
    preview_image_path: Optional[str] = None
    created_at: datetime
    creator: UserProfile

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class MapListResponse(BaseModel):
    """Schema for paginated map list response."""
    items: List[MapListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class MapDetailResponse(MapResponse):
    """Extended map response with ratings and comments."""
    ratings: List['RatingResponse'] = []
    comments: List['CommentResponse'] = []


# =============================================================================
# Rating Schemas
# =============================================================================

class RatingBase(BaseModel):
    """Base rating schema."""
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Rating value from 1 to 5"
    )


class RatingCreate(RatingBase):
    """Schema for rating creation."""
    pass  # rating is the only field needed


class RatingResponse(RatingBase):
    """Schema for rating response."""
    id: int
    user_id: int
    map_id: int
    user: UserProfile
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""
        from_attributes = True


# =============================================================================
# Comment Schemas
# =============================================================================

class CommentBase(BaseModel):
    """Base comment schema."""
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Comment text content"
    )


class CommentCreate(CommentBase):
    """Schema for comment creation."""
    pass  # content is the only field needed


class CommentUpdate(CommentBase):
    """Schema for comment update."""
    pass


class CommentResponse(CommentBase):
    """Schema for comment response."""
    id: int
    user_id: int
    map_id: int
    author: UserProfile
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""
        from_attributes = True


# =============================================================================
# Search and Filter Schemas
# =============================================================================

class MapSearchQuery(BaseModel):
    """Schema for map search and filter parameters."""
    terrain_type: Optional[str] = Field(
        None,
        description="Filter by terrain type"
    )
    size: Optional[int] = Field(
        None,
        ge=512,
        le=4096,
        description="Filter by map size"
    )
    player_count: Optional[int] = Field(
        None,
        ge=1,
        le=32,
        description="Filter by player count"
    )
    min_rating: Optional[float] = Field(
        None,
        ge=0.0,
        le=5.0,
        description="Minimum average rating"
    )
    author: Optional[str] = Field(
        None,
        description="Filter by author name"
    )
    search: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Search in name and description"
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="Sort field (created_at, rating, downloads, name)"
    )
    sort_order: Optional[str] = Field(
        "desc",
        description="Sort order (asc, desc)"
    )


# =============================================================================
# Token Schemas
# =============================================================================

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Schema for token payload data."""
    username: Optional[str] = None
    user_id: Optional[int] = None


# =============================================================================
# Generic Response Schemas
# =============================================================================

class MessageResponse(BaseModel):
    """Schema for simple message responses."""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    detail: Optional[str] = None


# =============================================================================
# Forward references for circular dependencies
# =============================================================================

# Update forward references
MapDetailResponse.model_rebuild()


# =============================================================================
# Schema Examples for Documentation
# =============================================================================

# Example data for API documentation
_USER_CREATE_EXAMPLE = {
    "username": "mapper123",
    "email": "mapper@example.com",
    "password": "securepassword123"
}

_USER_LOGIN_EXAMPLE = {
    "username": "mapper123",
    "password": "securepassword123"
}

_MAP_CREATE_EXAMPLE = {
    "name": "Tropical Islands",
    "shortname": "tropical_islands_v1",
    "description": "A beautiful tropical island map perfect for naval battles",
    "author": "MasterMapper",
    "version": "1.0",
    "generation_params": {
        "size": 1024,
        "terrain_type": "islands",
        "player_count": 4,
        "noise_strength": 5.0,
        "height_variation": 0.5,
        "water_level": 0.6,
        "metal_spots": 50,
        "metal_strength": 1.0,
        "geo_spots": 8,
        "start_positions": "symmetric"
    },
    "bar_info": {
        "mapx": 16,
        "mapy": 16,
        "maxplayers": 4,
        "gravity": 100,
        "tidalstrength": 100,
        "maxmetal": 100
    }
}

_RATING_CREATE_EXAMPLE = {
    "rating": 5
}

_COMMENT_CREATE_EXAMPLE = {
    "content": "Great map! Love the layout and metal distribution."
}
