# Ratings and Comments System Testing Guide

This document describes the testing approach for the rating and comment system in the BAR Community Map Sharing Portal.

## Overview

The rating and comment system allows authenticated users to:
- Submit ratings (1-5 stars) on maps
- Submit comments on maps
- Edit their own comments
- Delete their own comments
- View all ratings and comments on a map

## Test Script

### Automated Test: `test_ratings_comments.sh`

A comprehensive bash script that tests all rating and comment functionality end-to-end.

#### Running the Test

```bash
# Prerequisites:
# 1. Backend server must be running
cd backend && uvicorn main:app --reload

# 2. In another terminal, run the test
./test_ratings_comments.sh
```

#### Test Coverage

The automated script tests:

1. **Setup** (lines 44-123)
   - Creates test user account
   - Uploads test map with preview image
   - Stores IDs for subsequent tests

2. **Rating without Authentication** (lines 125-144)
   - Attempts to submit rating without JWT token
   - Expects HTTP 401 Unauthorized
   - Verforms: `POST /api/maps/{map_id}/ratings` without auth header

3. **Rating with Authentication** (lines 146-175)
   - Submits rating with valid JWT token
   - Expects HTTP 200 OK
   - Verifies rating value in response

4. **Verify Rating on Map** (lines 177-210)
   - Retrieves map details via `GET /api/maps/{map_id}`
   - Verifies `average_rating` and `rating_count` fields
   - Confirms rating is reflected in map statistics

5. **Comment without Authentication** (lines 212-231)
   - Attempts to submit comment without JWT token
   - Expects HTTP 401 Unauthorized
   - Performs: `POST /api/maps/{map_id}/comments` without auth header

6. **Comment with Authentication** (lines 233-268)
   - Submits comment with valid JWT token
   - Expects HTTP 201 Created
   - Stores comment ID for edit/delete tests

7. **Verify Comment in Thread** (lines 270-299)
   - Retrieves all comments via `GET /api/maps/{map_id}/comments`
   - Verifies comment appears in response array
   - Confirms comment content matches submission

8. **Edit Comment** (lines 301-340)
   - Updates comment via `PUT /api/maps/{map_id}/comments/{comment_id}`
   - Expects HTTP 200 OK
   - Verifies updated content in response
   - Confirms comment author can edit their own comment

9. **Delete Comment** (lines 342-379)
   - Deletes comment via `DELETE /api/maps/{map_id}/comments/{comment_id}`
   - Expects HTTP 204 No Content
   - Verifies comment no longer appears in thread
   - Confirms comment author can delete their own comment

10. **Unauthorized Edit/Delete** (lines 381-438)
    - Creates second user account
    - Attempts to edit first user's comment with second user's token
    - Expects HTTP 403 Forbidden
    - Attempts to delete first user's comment with second user's token
    - Expects HTTP 403 Forbidden
    - Verifies authorization checks work correctly

11. **Rating Update** (lines 440-487)
    - Submits new rating for same user/map combination
    - Expects HTTP 200 OK (update, not create)
    - Verifies rating value changed
    - Confirms average rating recalculated correctly

## Manual Testing Guide

For manual browser-based testing, follow these steps:

### Prerequisites

1. Backend server running: `cd backend && uvicorn main:app --reload`
2. Browser open to: `http://localhost:8000/community`

### Test Steps

#### 1. Browse to Map Detail Page

```
1. Navigate to http://localhost:8000/community
2. Click on any map card to view map details
3. Verify map detail page loads with:
   - Map preview image
   - Map metadata (terrain, size, players)
   - Rating stars (interactive)
   - Comments section
```

**Expected Result**: Map detail page displays correctly with all elements.

#### 2. Submit Rating Without Authentication

```
1. Ensure you are logged out (click "Logout" if logged in)
2. Click on a star rating (e.g., 4 stars)
3. Observe the behavior
```

**Expected Result**:
- Login modal appears
- Rating is NOT submitted
- Message indicates authentication required

#### 3. Login and Submit Rating

```
1. In the login modal, register a new account or login
2. After successful login, click on a star rating (e.g., 5 stars)
3. Observe the stars fill with gold color
4. Check for success notification
5. Verify the displayed average rating updates
```

**Expected Result**:
- Stars fill with gold color on hover and click
- Success notification appears: "Rating submitted successfully!"
- Message displays: "You rated this map 5 stars!"
- Average rating and rating count update on the page

#### 4. Verify Rating Appears on Map

```
1. Note the current average rating and count
2. Refresh the page (F5)
3. Verify the rating persists
4. Navigate back to browse view
5. Find the map in the grid
6. Verify the rating appears on the map card
```

**Expected Result**:
- Rating persists across page refresh
- Map card in browse view shows correct star rating
- Rating format is correct (e.g., "⭐ ★★★★☆ 4.5")

#### 5. Submit a Comment

```
1. On the map detail page, scroll to comments section
2. In the "Add a Comment" textarea, type: "Great map layout!"
3. Click "💬 Post Comment" button
4. Wait for submission
```

**Expected Result**:
- Loading state during submission
- Success notification appears: "Comment posted successfully!"
- Comment appears in the comments list
- Comment shows:
  - Your username as author
  - Current date
  - The comment content
  - Edit and Delete buttons (since you're the author)

#### 6. Verify Comment Appears in Thread

```
1. Scroll through the comments section
2. Find your submitted comment
3. Verify all details are correct
4. Refresh the page (F5)
5. Verify comment persists
```

**Expected Result**:
- Comment appears at top of thread (newest first)
- Author username is correct
- Timestamp is current
- Content matches exactly what you typed
- Comment persists after page refresh

#### 7. Edit an Existing Comment

```
1. Find a comment you authored (has Edit/Delete buttons)
2. Click "Edit" button
3. Observe the edit form appears
4. Modify the text in the textarea
5. Click "Save" button
```

**Expected Result**:
- Original comment content hides
- Edit form appears with textarea pre-filled
- "Save" and "Cancel" buttons visible
- After clicking save:
  - Success notification: "Comment updated successfully!"
  - Comment content updates to new text
  - "Updated" timestamp reflects edit time

#### 8. Delete a Comment

```
1. Find a comment you authored
2. Click "Delete" button
3. Confirm deletion in the dialog
```

**Expected Result**:
- Confirmation dialog appears: "Are you sure you want to delete this comment?"
- After confirming:
  - Success notification: "Comment deleted successfully!"
  - Comment immediately disappears from thread
  - Other comments remain unaffected

## API Endpoints Reference

### Rating Endpoints

#### Submit/Update Rating
```
POST /api/maps/{map_id}/ratings
Authorization: Bearer {jwt_token}
Content-Type: application/json

Body: {
  "rating": 5  // 1-5
}

Response: 200 OK (on create or update)
{
  "id": 1,
  "user_id": 5,
  "map_id": 10,
  "rating": 5,
  "user": {
    "id": 5,
    "username": "testuser"
  },
  "created_at": "2026-01-22T10:00:00Z",
  "updated_at": "2026-01-22T10:00:00Z"
}
```

### Comment Endpoints

#### Submit Comment
```
POST /api/maps/{map_id}/comments
Authorization: Bearer {jwt_token}
Content-Type: application/json

Body: {
  "content": "Great map!"
}

Response: 201 Created
{
  "id": 1,
  "user_id": 5,
  "map_id": 10,
  "content": "Great map!",
  "author": {
    "id": 5,
    "username": "testuser"
  },
  "created_at": "2026-01-22T10:00:00Z",
  "updated_at": "2026-01-22T10:00:00Z"
}
```

#### Get Comments
```
GET /api/maps/{map_id}/comments?limit=50&sort_by=created_at&sort_order=desc

Response: 200 OK
[
  {
    "id": 1,
    "user_id": 5,
    "map_id": 10,
    "content": "Great map!",
    "author": {
      "id": 5,
      "username": "testuser"
    },
    "created_at": "2026-01-22T10:00:00Z",
    "updated_at": "2026-01-22T10:00:00Z"
  }
]
```

#### Update Comment
```
PUT /api/maps/{map_id}/comments/{comment_id}
Authorization: Bearer {jwt_token}
Content-Type: application/json

Body: {
  "content": "Updated comment text"
}

Response: 200 OK
(returns updated comment object)
```

#### Delete Comment
```
DELETE /api/maps/{map_id}/comments/{comment_id}
Authorization: Bearer {jwt_token}

Response: 204 No Content
```

## Authorization Rules

### Ratings
- **Required**: Must be authenticated (JWT token required)
- **One per user**: Each user can only have one rating per map
- **Updates allowed**: Submitting a new rating updates existing one

### Comments
- **Submit**: Must be authenticated
- **View**: No authentication required (public)
- **Edit**: Only comment author can edit
- **Delete**: Only comment author can delete

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```
**Cause**: Missing or invalid JWT token

### 403 Forbidden
```json
{
  "detail": "You can only update your own comments"
}
```
**Cause**: Attempting to edit/delete another user's comment

### 404 Not Found
```json
{
  "detail": "Map with ID 999 not found"
}
```
**Cause**: Map or comment doesn't exist

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "rating"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error.number.not_ge"
    }
  ]
}
```
**Cause**: Invalid input (e.g., rating < 1 or > 5)

## Troubleshooting

### Test Failures

**Server Not Running**
```bash
Error: Server is not running
Solution: cd backend && uvicorn main:app --reload
```

**Port Already in Use**
```bash
Error: Address already in use
Solution: Kill existing process or use different port
```

**Database Errors**
```bash
Error: Database connection failed
Solution:
1. Check PostgreSQL is running
2. Verify database exists: psql -l
3. Check DATABASE_URL in .env
```

**Authentication Failures**
```bash
Error: 401 Unauthorized
Solution:
1. Verify JWT token is valid
2. Check token expiration
3. Ensure Authorization header format: "Bearer {token}"
```

## Code Quality Checklist

- [x] No console.log statements in production code
- [x] Proper error handling for all API calls
- [x] User-friendly error messages
- [x] Loading states for async operations
- [x] Success notifications for user actions
- [x] Input validation on frontend
- [x] Authorization checks on backend
- [x] Ownership verification for edits/deletes
- [x] Appropriate HTTP status codes
- [x] Consistent response formats

## Testing Best Practices

1. **Test Authentication Flows**
   - Always test both authenticated and unauthenticated scenarios
   - Verify 401 responses for missing auth
   - Verify 403 responses for unauthorized access

2. **Test Data Persistence**
   - Refresh pages to verify data persists
   - Navigate away and back to confirm state
   - Check database directly if needed

3. **Test Edge Cases**
   - Empty comments
   - Very long comments
   - Special characters in content
   - Rapid repeated submissions

4. **Test User Experience**
   - Loading states should be clear
   - Error messages should be helpful
   - Success feedback should be immediate
   - UI should respond appropriately

## Integration with Other Features

### Map Upload
- When uploading a map, initial rating_count is 0
- average_rating is NULL until first rating

### Search/Filter
- Maps can be sorted by rating (highest to lowest)
- Filter by minimum rating (e.g., "4+ stars")

### Download Tracking
- Ratings and downloads are independent metrics
- High downloads don't necessarily mean high ratings

### User Profiles
- "My Maps" shows all maps uploaded by user
- Comments show username, not full email

## Performance Considerations

### Rating Calculation
- Average rating is calculated on-the-fly
- Caching could be added for high-traffic maps
- Rating counts are efficient (COUNT query)

### Comment Pagination
- Comments endpoint supports pagination
- Default limit is 50, max is 100
- Use skip/limit for large comment threads

### Database Indexes
- Index on (map_id, user_id) for ratings (prevent duplicates)
- Index on (map_id) for comments retrieval
- Index on (user_id) for user's ratings lookup

## Security Considerations

### Input Validation
- Rating must be 1-5 (enforced by Pydantic schema)
- Comment content has max length (database constraint)
- HTML escaping prevents XSS attacks

### Rate Limiting
- Consider adding rate limiting for:
  - Rating submissions (prevent rating spam)
  - Comment submissions (prevent comment spam)

### Content Moderation
- No profanity filter currently implemented
- Consider adding:
  - Flagged comment system
  - Admin moderation queue
  - Automated content filtering

## Future Enhancements

### Potential Improvements
1. **Rating Breakdown**
   - Show distribution (how many 5-star, 4-star, etc.)
   - Visual histogram of ratings

2. **Comment Threading**
   - Nested replies to comments
   - @mention other users
   - Like/upvote on comments

3. **Rating Categories**
   - Rate by aspects: gameplay, visuals, balance
   - Separate scores for each category

4. **Helpful Ratings**
   - Mark comments as "helpful"
   - Sort comments by helpfulness

5. **Email Notifications**
   - Notify map author of new ratings/comments
   - Notify users of replies to their comments
