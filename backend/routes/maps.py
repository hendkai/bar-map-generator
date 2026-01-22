"""
Map routes for BAR Community Map Sharing Portal.
Handles map upload, listing, search, detail, and download endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from database import get_db
from models import Map, User
from schemas import MapCreate, MapResponse, MapListItem, MapListResponse, UserProfile
from auth import get_current_user
from storage import save_uploaded_file, save_preview_image, delete_file, get_upload_dir
from config import settings


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(
    prefix="/maps",
    tags=["maps"],
)


# =============================================================================
# Map Upload Endpoint
# =============================================================================

@router.post(
    "/upload",
    response_model=MapResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new map",
    description="Upload a .sd7 map file with metadata. Requires authentication.",
    responses={
        201: {"description": "Map uploaded successfully"},
        401: {"description": "Authentication required"},
        413: {"description": "File too large"},
        415: {"description": "Invalid file type"},
        422: {"description": "Validation error"}
    }
)
async def upload_map(
    file: UploadFile = File(..., description="Map file (.sd7)"),
    name: str = Form(..., description="Map display name"),
    shortname: str = Form(..., description="Short identifier"),
    description: Optional[str] = Form(None, description="Detailed map description"),
    author: str = Form(..., description="Map author name"),
    version: str = Form(default="1.0", description="Map version"),
    generation_params: str = Form(..., description="JSON string of generation parameters"),
    bar_info: str = Form(..., description="JSON string of BAR map information"),
    preview_image: Optional[UploadFile] = File(None, description="Optional preview image"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MapResponse:
    """
    Upload a new map to the community portal.

    This endpoint accepts a multipart/form-data upload with:
    - file: The .sd7 map file (required)
    - name: Map display name (required)
    - shortname: Short identifier (required)
    - description: Detailed description (optional)
    - author: Map author name (required)
    - version: Map version (default: "1.0")
    - generation_params: JSON string with generation parameters (required)
    - bar_info: JSON string with BAR-specific map info (required)
    - preview_image: Optional preview image file

    Args:
        file: Uploaded .sd7 map file
        name: Map display name
        shortname: Short identifier for the map
        description: Detailed map description
        author: Map author name
        version: Map version string
        generation_params: JSON string of MapGenerationParams
        bar_info: JSON string of BARMapInfo
        preview_image: Optional preview image file
        current_user: Authenticated user (injected by dependency)
        db: Database session (injected by dependency)

    Returns:
        MapResponse: Created map with all details

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 413: If file too large
        HTTPException 415: If invalid file type
        HTTPException 422: If validation fails
        HTTPException 500: If server error occurs
    """
    try:
        # Parse JSON strings for nested data
        try:
            generation_data = json.loads(generation_params)
            bar_data = json.loads(bar_info)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid JSON in generation_params or bar_info: {str(e)}"
            )

        # Save the map file
        file_relative_path, file_full_path = await save_uploaded_file(file, subdirectory="maps")

        # Save preview image if provided
        preview_image_path = None
        if preview_image:
            preview_data = await preview_image.read()
            # We'll need the map_id, so we'll save this after creating the map record
            # For now, store the data to save later
            preview_data_to_save = preview_data
        else:
            preview_data_to_save = None

        # Create map record in database
        new_map = Map(
            name=name,
            shortname=shortname,
            description=description,
            author=author,
            version=version,
            creator_id=current_user.id,

            # BAR-specific fields
            mapx=bar_data.get("mapx", 16),
            mapy=bar_data.get("mapy", 16),
            maxplayers=bar_data.get("maxplayers", generation_data.get("player_count", 4)),
            gravity=bar_data.get("gravity", 100),
            tidalstrength=bar_data.get("tidalstrength", 100),
            maxmetal=bar_data.get("maxmetal", 100),

            # Generation parameters
            size=generation_data.get("size", 1024),
            terrain_type=generation_data.get("terrain_type", "continental"),
            player_count=generation_data.get("player_count", 4),
            noise_strength=generation_data.get("noise_strength", 5.0),
            height_variation=generation_data.get("height_variation", 0.5),
            water_level=generation_data.get("water_level", 0.3),
            metal_spots=generation_data.get("metal_spots", 50),
            metal_strength=generation_data.get("metal_strength", 1.0),
            geo_spots=generation_data.get("geo_spots", 10),
            start_positions=generation_data.get("start_positions", "symmetric"),

            # File storage
            file_path=file_relative_path,

            # Statistics (defaults)
            download_count=0,
            average_rating=0.0,
            rating_count=0,
        )

        db.add(new_map)
        db.commit()
        db.refresh(new_map)

        # Save preview image now that we have the map_id
        if preview_data_to_save:
            try:
                preview_image_path = await save_preview_image(
                    preview_data_to_save,
                    new_map.id,
                    extension="png"
                )
                # Update map with preview image path
                new_map.preview_image_path = preview_image_path
                db.commit()
                db.refresh(new_map)
            except Exception as e:
                # Log error but don't fail the upload if preview fails
                pass

        # Build response with creator profile
        response_data = {
            "id": new_map.id,
            "name": new_map.name,
            "shortname": new_map.shortname,
            "description": new_map.description,
            "author": new_map.author,
            "version": new_map.version,
            "creator_id": new_map.creator_id,
            "creator": UserProfile.model_validate(current_user),

            # BAR-specific fields
            "mapx": new_map.mapx,
            "mapy": new_map.mapy,
            "maxplayers": new_map.maxplayers,
            "gravity": new_map.gravity,
            "tidalstrength": new_map.tidalstrength,
            "maxmetal": new_map.maxmetal,

            # Generation parameters
            "size": new_map.size,
            "terrain_type": new_map.terrain_type,
            "player_count": new_map.player_count,
            "noise_strength": new_map.noise_strength,
            "height_variation": new_map.height_variation,
            "water_level": new_map.water_level,
            "metal_spots": new_map.metal_spots,
            "metal_strength": new_map.metal_strength,
            "geo_spots": new_map.geo_spots,
            "start_positions": new_map.start_positions,

            # Statistics
            "download_count": new_map.download_count,
            "average_rating": new_map.average_rating,
            "rating_count": new_map.rating_count,

            # File paths
            "file_path": new_map.file_path,
            "preview_image_path": new_map.preview_image_path,

            # Metadata
            "created_at": new_map.created_at,
            "updated_at": new_map.updated_at,
        }

        return MapResponse(**response_data)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Clean up uploaded file if database operation fails
        if 'file_relative_path' in locals():
            delete_file(file_relative_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload map: {str(e)}"
        )


# =============================================================================
# Map Listing Endpoint
# =============================================================================

@router.get(
    "",
    response_model=MapListResponse,
    summary="List maps with pagination",
    description="Retrieve a paginated list of community maps. Supports optional filtering by terrain type, size, player count, author, and minimum rating.",
    responses={
        200: {"description": "Maps retrieved successfully"},
        400: {"description": "Invalid query parameters"},
    }
)
async def list_maps(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page (max 100)"),
    terrain_type: Optional[str] = Query(None, description="Filter by terrain type"),
    size: Optional[int] = Query(None, ge=512, le=4096, description="Filter by map size"),
    player_count: Optional[int] = Query(None, ge=1, le=32, description="Filter by player count"),
    min_rating: Optional[float] = Query(None, ge=0.0, le=5.0, description="Minimum average rating"),
    author: Optional[str] = Query(None, description="Filter by author name"),
    creator_id: Optional[int] = Query(None, description="Filter by creator user ID"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in name and description"),
    sort_by: Optional[str] = Query("created_at", description="Sort field (created_at, rating, downloads, name)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    db: Session = Depends(get_db)
) -> MapListResponse:
    """
    List maps with pagination and optional filtering.

    This endpoint returns a paginated list of maps with support for:
    - Pagination (page number and page size)
    - Filtering by terrain type, size, player count, author, creator_id, minimum rating
    - Full-text search in map name and description
    - Sorting by creation date, rating, downloads, or name

    Args:
        page: Page number (1-indexed)
        limit: Number of items per page (max 100)
        terrain_type: Optional filter by terrain type (e.g., "continental", "islands")
        size: Optional filter by map size in pixels (e.g., 1024, 2048)
        player_count: Optional filter by number of players
        min_rating: Optional minimum average rating (0.0 - 5.0)
        author: Optional filter by author name (case-insensitive partial match)
        creator_id: Optional filter by creator user ID (exact match)
        search: Optional search string for name and description fields
        sort_by: Field to sort by (created_at, rating, downloads, name)
        sort_order: Sort order (asc or desc)
        db: Database session (injected by dependency)

    Returns:
        MapListResponse: Paginated list of maps with metadata

    Raises:
        HTTPException 400: If query parameters are invalid
        HTTPException 500: If server error occurs
    """
    try:
        # Build base query
        query = db.query(Map)

        # Apply filters
        if terrain_type:
            query = query.filter(Map.terrain_type == terrain_type)

        if size:
            query = query.filter(Map.size == size)

        if player_count:
            query = query.filter(Map.player_count == player_count)

        if min_rating is not None:
            query = query.filter(Map.average_rating >= min_rating)

        if author:
            query = query.filter(Map.author.ilike(f"%{author}%"))

        if creator_id is not None:
            query = query.filter(Map.creator_id == creator_id)

        if search:
            query = query.filter(
                (Map.name.ilike(f"%{search}%")) |
                (Map.description.ilike(f"%{search}%"))
            )

        # Validate sort parameters
        valid_sort_fields = {
            "created_at": Map.created_at,
            "rating": Map.average_rating,
            "downloads": Map.download_count,
            "name": Map.name
        }

        if sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields.keys())}"
            )

        if sort_order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid sort_order. Must be 'asc' or 'desc'"
            )

        # Apply sorting
        sort_field = valid_sort_fields[sort_by]
        if sort_order == "asc":
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())

        # Calculate total items before pagination
        total = query.count()

        # Calculate pagination
        offset = (page - 1) * limit

        # Fetch paginated results
        maps = query.offset(offset).limit(limit).all()

        # Build response items
        items = []
        for map_obj in maps:
            # Build creator profile
            creator_profile = UserProfile(
                id=map_obj.creator.id,
                username=map_obj.creator.username
            )

            # Build map list item
            item = MapListItem(
                id=map_obj.id,
                name=map_obj.name,
                shortname=map_obj.shortname,
                author=map_obj.author,
                terrain_type=map_obj.terrain_type,
                size=map_obj.size,
                player_count=map_obj.player_count,
                maxplayers=map_obj.maxplayers,
                average_rating=map_obj.average_rating,
                rating_count=map_obj.rating_count,
                download_count=map_obj.download_count,
                preview_image_path=map_obj.preview_image_path,
                created_at=map_obj.created_at,
                creator=creator_profile
            )
            items.append(item)

        # Calculate total pages
        total_pages = (total + limit - 1) // limit if total > 0 else 0

        # Build response
        return MapListResponse(
            items=items,
            total=total,
            page=page,
            page_size=limit,
            total_pages=total_pages
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve maps: {str(e)}"
        )


# =============================================================================
# Map Detail Endpoint
# =============================================================================

@router.get(
    "/{map_id}",
    response_model=MapResponse,
    summary="Get map details",
    description="Retrieve detailed information about a specific map including all metadata, generation parameters, and statistics.",
    responses={
        200: {"description": "Map details retrieved successfully"},
        404: {"description": "Map not found"}
    }
)
async def get_map_detail(
    map_id: int,
    db: Session = Depends(get_db)
) -> MapResponse:
    """
    Retrieve detailed information about a specific map.

    This endpoint returns complete map metadata including:
    - Basic map information (name, author, description, version)
    - BAR-specific fields (dimensions, max players, game settings)
    - Generation parameters (terrain type, size, player count, etc.)
    - Statistics (downloads, ratings)
    - File paths
    - Creator information

    Args:
        map_id: ID of the map to retrieve
        db: Database session (injected by dependency)

    Returns:
        MapResponse: Complete map details

    Raises:
        HTTPException 404: If map with specified ID doesn't exist
        HTTPException 500: If server error occurs
    """
    try:
        # Query map by ID
        map_obj = db.query(Map).filter(Map.id == map_id).first()

        if not map_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Map with ID {map_id} not found"
            )

        # Build creator profile
        creator_profile = UserProfile(
            id=map_obj.creator.id,
            username=map_obj.creator.username
        )

        # Build response data
        response_data = {
            "id": map_obj.id,
            "name": map_obj.name,
            "shortname": map_obj.shortname,
            "description": map_obj.description,
            "author": map_obj.author,
            "version": map_obj.version,
            "creator_id": map_obj.creator_id,
            "creator": creator_profile,

            # BAR-specific fields
            "mapx": map_obj.mapx,
            "mapy": map_obj.mapy,
            "maxplayers": map_obj.maxplayers,
            "gravity": map_obj.gravity,
            "tidalstrength": map_obj.tidalstrength,
            "maxmetal": map_obj.maxmetal,

            # Generation parameters
            "size": map_obj.size,
            "terrain_type": map_obj.terrain_type,
            "player_count": map_obj.player_count,
            "noise_strength": map_obj.noise_strength,
            "height_variation": map_obj.height_variation,
            "water_level": map_obj.water_level,
            "metal_spots": map_obj.metal_spots,
            "metal_strength": map_obj.metal_strength,
            "geo_spots": map_obj.geo_spots,
            "start_positions": map_obj.start_positions,

            # Statistics
            "download_count": map_obj.download_count,
            "average_rating": map_obj.average_rating,
            "rating_count": map_obj.rating_count,

            # File paths
            "file_path": map_obj.file_path,
            "preview_image_path": map_obj.preview_image_path,

            # Metadata
            "created_at": map_obj.created_at,
            "updated_at": map_obj.updated_at,
        }

        return MapResponse(**response_data)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve map details: {str(e)}"
        )


# =============================================================================
# Map Download Endpoint
# =============================================================================

@router.get(
    "/{map_id}/download",
    summary="Download map file",
    description="Download the .sd7 map file. The download count is incremented each time this endpoint is called.",
    responses={
        200: {"description": "Map file downloaded successfully", "content": {"application/octet-stream": {}}},
        404: {"description": "Map not found"}
    }
)
async def download_map(
    map_id: int,
    db: Session = Depends(get_db)
):
    """
    Download the .sd7 map file for a specific map.

    This endpoint returns the actual map file as a file download.
    The file is served with appropriate headers for browser download.
    The download count is automatically incremented each time this endpoint is called.

    Args:
        map_id: ID of the map to download
        db: Database session (injected by dependency)

    Returns:
        FileResponse: The map file for download

    Raises:
        HTTPException 404: If map or file doesn't exist
        HTTPException 500: If server error occurs
    """
    try:
        # Query map by ID
        map_obj = db.query(Map).filter(Map.id == map_id).first()

        if not map_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Map with ID {map_id} not found"
            )

        # Increment download count
        map_obj.download_count += 1
        db.commit()

        # Get the full file path
        upload_dir = get_upload_dir()
        file_path = upload_dir / map_obj.file_path

        # Check if file exists
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Map file not found on server"
            )

        # Generate filename for download (use map name and version)
        download_filename = f"{map_obj.shortname}_{map_obj.version}.sd7"

        # Return file response
        return FileResponse(
            path=str(file_path),
            filename=download_filename,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"'
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download map: {str(e)}"
        )


# =============================================================================
# Rating Statistics Utilities
# =============================================================================

def update_map_rating_stats(db: Session, map_obj: Map) -> None:
    """
    Recalculate and update the map's cached average rating and rating count.

    This function queries all ratings for the map and updates the cached
    average_rating and rating_count fields on the map object. These cached
    values are used for efficient sorting and filtering in map listings.

    The caching strategy avoids expensive aggregate queries on each map listing,
    instead updating the cached values only when ratings change.

    Args:
        db: Database session
        map_obj: Map object to update

    Example:
        >>> map_obj = db.query(Map).filter(Map.id == map_id).first()
        >>> update_map_rating_stats(db, map_obj)
        >>> # map_obj.average_rating and map_obj.rating_count are now updated
    """
    from models import Rating

    # Get all ratings for this map
    ratings = db.query(Rating).filter(Rating.map_id == map_obj.id).all()

    # Update rating count
    map_obj.rating_count = len(ratings)

    # Calculate and cache average rating
    if map_obj.rating_count > 0:
        total = sum(r.rating for r in ratings)
        map_obj.average_rating = round(total / map_obj.rating_count, 2)
    else:
        map_obj.average_rating = 0.0

    # Commit changes to persist cached values
    db.commit()

    # Refresh to ensure we have the latest values
    db.refresh(map_obj)
