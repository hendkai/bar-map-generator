"""
Rating and Comment routes for BAR Community Map Sharing Portal.
Handles rating submission, update, and comment submission/retrieval endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Map, Rating, User, Comment
from schemas import (
    RatingCreate, RatingResponse, UserProfile,
    CommentCreate, CommentUpdate, CommentResponse
)
from auth import get_current_user
from routes.maps import update_map_rating_stats


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(
    prefix="/maps",
    tags=["ratings", "comments"],
)


# =============================================================================
# Rating Submission/Update Endpoint
# =============================================================================

@router.post(
    "/{map_id}/ratings",
    response_model=RatingResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit or update a rating for a map",
    description="Submit a new rating or update an existing rating for a map. Requires authentication. Each user can only have one rating per map.",
    responses={
        200: {"description": "Rating submitted/updated successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Map not found"},
        422: {"description": "Validation error"}
    }
)
async def submit_rating(
    map_id: int,
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RatingResponse:
    """
    Submit a new rating or update an existing rating for a map.

    This endpoint allows authenticated users to rate maps on a scale of 1-5.
    If the user has already rated the map, their existing rating will be updated.
    The map's average_rating and rating_count fields are automatically recalculated.

    Args:
        map_id: ID of the map to rate
        rating_data: Rating data (rating value 1-5)
        current_user: Authenticated user (injected by dependency)
        db: Database session (injected by dependency)

    Returns:
        RatingResponse: The created or updated rating

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If map doesn't exist
        HTTPException 422: If validation fails
        HTTPException 500: If server error occurs
    """
    try:
        # Verify map exists
        map_obj = db.query(Map).filter(Map.id == map_id).first()
        if not map_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Map with ID {map_id} not found"
            )

        # Check if user has already rated this map
        existing_rating = db.query(Rating).filter(
            Rating.user_id == current_user.id,
            Rating.map_id == map_id
        ).first()

        if existing_rating:
            # Update existing rating
            old_rating_value = existing_rating.rating
            existing_rating.rating = rating_data.rating
            db.commit()
            db.refresh(existing_rating)

            # Recalculate map average rating
            update_map_rating_stats(db, map_obj)

            # Build response
            user_profile = UserProfile(
                id=current_user.id,
                username=current_user.username
            )

            response_data = {
                "id": existing_rating.id,
                "user_id": existing_rating.user_id,
                "map_id": existing_rating.map_id,
                "rating": existing_rating.rating,
                "user": user_profile,
                "created_at": existing_rating.created_at,
                "updated_at": existing_rating.updated_at
            }

            return RatingResponse(**response_data)

        else:
            # Create new rating
            new_rating = Rating(
                user_id=current_user.id,
                map_id=map_id,
                rating=rating_data.rating
            )

            db.add(new_rating)
            db.commit()
            db.refresh(new_rating)

            # Recalculate map average rating
            update_map_rating_stats(db, map_obj)

            # Build response
            user_profile = UserProfile(
                id=current_user.id,
                username=current_user.username
            )

            response_data = {
                "id": new_rating.id,
                "user_id": new_rating.user_id,
                "map_id": new_rating.map_id,
                "rating": new_rating.rating,
                "user": user_profile,
                "created_at": new_rating.created_at,
                "updated_at": new_rating.updated_at
            }

            return RatingResponse(**response_data)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit rating: {str(e)}"
        )


# =============================================================================
# Comment Submission Endpoint
# =============================================================================

@router.post(
    "/{map_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a comment for a map",
    description="Submit a new comment for a map. Requires authentication.",
    responses={
        201: {"description": "Comment submitted successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Map not found"},
        422: {"description": "Validation error"}
    }
)
async def submit_comment(
    map_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CommentResponse:
    """
    Submit a new comment for a map.

    This endpoint allows authenticated users to comment on maps.
    Comments are public and visible to all users.

    Args:
        map_id: ID of the map to comment on
        comment_data: Comment data (content text)
        current_user: Authenticated user (injected by dependency)
        db: Database session (injected by dependency)

    Returns:
        CommentResponse: The created comment

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If map doesn't exist
        HTTPException 422: If validation fails
        HTTPException 500: If server error occurs
    """
    try:
        # Verify map exists
        map_obj = db.query(Map).filter(Map.id == map_id).first()
        if not map_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Map with ID {map_id} not found"
            )

        # Create new comment
        new_comment = Comment(
            user_id=current_user.id,
            map_id=map_id,
            content=comment_data.content
        )

        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)

        # Build response
        author_profile = UserProfile(
            id=current_user.id,
            username=current_user.username
        )

        response_data = {
            "id": new_comment.id,
            "user_id": new_comment.user_id,
            "map_id": new_comment.map_id,
            "content": new_comment.content,
            "author": author_profile,
            "created_at": new_comment.created_at,
            "updated_at": new_comment.updated_at
        }

        return CommentResponse(**response_data)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit comment: {str(e)}"
        )


# =============================================================================
# Comment Retrieval Endpoint
# =============================================================================

@router.get(
    "/{map_id}/comments",
    response_model=List[CommentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all comments for a map",
    description="Retrieve all comments for a specific map. Supports pagination and sorting.",
    responses={
        200: {"description": "Comments retrieved successfully"},
        404: {"description": "Map not found"}
    }
)
async def get_comments(
    map_id: int,
    skip: int = Query(0, ge=0, description="Number of comments to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of comments to return"),
    sort_by: Optional[str] = Query("created_at", description="Sort field (created_at, updated_at)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    db: Session = Depends(get_db)
) -> List[CommentResponse]:
    """
    Retrieve all comments for a specific map.

    This endpoint allows anyone to view comments on a map.
    Results are paginated and can be sorted by creation or update time.

    Args:
        map_id: ID of the map to get comments for
        skip: Number of comments to skip (for pagination)
        limit: Maximum number of comments to return (default: 50, max: 100)
        sort_by: Field to sort by (created_at, updated_at)
        sort_order: Sort direction (asc or desc)
        db: Database session (injected by dependency)

    Returns:
        List[CommentResponse]: List of comments for the map

    Raises:
        HTTPException 404: If map doesn't exist
        HTTPException 500: If server error occurs
    """
    try:
        # Verify map exists
        map_obj = db.query(Map).filter(Map.id == map_id).first()
        if not map_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Map with ID {map_id} not found"
            )

        # Build query
        query = db.query(Comment).filter(Comment.map_id == map_id)

        # Apply sorting
        sort_column = Comment.created_at if sort_by == "created_at" else Comment.updated_at
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        comments = query.offset(skip).limit(limit).all()

        # Build response list
        response_list = []
        for comment in comments:
            author_profile = UserProfile(
                id=comment.author.id,
                username=comment.author.username
            )

            response_data = {
                "id": comment.id,
                "user_id": comment.user_id,
                "map_id": comment.map_id,
                "content": comment.content,
                "author": author_profile,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at
            }

            response_list.append(CommentResponse(**response_data))

        return response_list

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve comments: {str(e)}"
        )


# =============================================================================
# Comment Update Endpoint
# =============================================================================

@router.put(
    "/{map_id}/comments/{comment_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a comment",
    description="Update an existing comment. Only the comment author can update their own comment.",
    responses={
        200: {"description": "Comment updated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Not authorized to update this comment"},
        404: {"description": "Comment or map not found"},
        422: {"description": "Validation error"}
    }
)
async def update_comment(
    map_id: int,
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CommentResponse:
    """
    Update an existing comment.

    This endpoint allows the comment author to edit their own comment.

    Args:
        map_id: ID of the map
        comment_id: ID of the comment to update
        comment_data: Updated comment data
        current_user: Authenticated user (injected by dependency)
        db: Database session (injected by dependency)

    Returns:
        CommentResponse: The updated comment

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If user is not the comment author
        HTTPException 404: If comment or map doesn't exist
        HTTPException 422: If validation fails
        HTTPException 500: If server error occurs
    """
    try:
        # Get comment
        comment = db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.map_id == map_id
        ).first()

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with ID {comment_id} not found for map {map_id}"
            )

        # Verify ownership
        if comment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own comments"
            )

        # Update comment
        comment.content = comment_data.content
        db.commit()
        db.refresh(comment)

        # Build response
        author_profile = UserProfile(
            id=comment.author.id,
            username=comment.author.username
        )

        response_data = {
            "id": comment.id,
            "user_id": comment.user_id,
            "map_id": comment.map_id,
            "content": comment.content,
            "author": author_profile,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at
        }

        return CommentResponse(**response_data)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update comment: {str(e)}"
        )


# =============================================================================
# Comment Deletion Endpoint
# =============================================================================

@router.delete(
    "/{map_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
    description="Delete an existing comment. Only the comment author can delete their own comment.",
    responses={
        204: {"description": "Comment deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Not authorized to delete this comment"},
        404: {"description": "Comment or map not found"}
    }
)
async def delete_comment(
    map_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> None:
    """
    Delete an existing comment.

    This endpoint allows the comment author to delete their own comment.

    Args:
        map_id: ID of the map
        comment_id: ID of the comment to delete
        current_user: Authenticated user (injected by dependency)
        db: Database session (injected by dependency)

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If user is not the comment author
        HTTPException 404: If comment or map doesn't exist
        HTTPException 500: If server error occurs
    """
    try:
        # Get comment
        comment = db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.map_id == map_id
        ).first()

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with ID {comment_id} not found for map {map_id}"
            )

        # Verify ownership
        if comment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own comments"
            )

        # Delete comment
        db.delete(comment)
        db.commit()

        return None

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete comment: {str(e)}"
        )

