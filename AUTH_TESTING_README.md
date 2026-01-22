# Authentication Flow Testing

This document describes the testing approach for the authentication system in the Community Map Sharing Portal.

## Test Overview

The authentication flow has been tested to verify:
1. User registration
2. User login
3. Token-based authentication
4. Protected route access
5. Map upload with authentication
6. "My Maps" filtering by creator_id
7. Token persistence (logout/login)
8. Duplicate registration prevention

## Running the Tests

### Prerequisites

1. **Start the backend server:**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

   The server should run on `http://localhost:8000`

2. **Ensure database is running:**
   ```bash
   docker-compose up -d db
   ```

### Automated Test Script

Run the comprehensive authentication flow test:

```bash
./test_auth_flow.sh
```

This script will:
- Create a test user with a unique username (timestamp-based)
- Register the user
- Test login with correct credentials
- Test login with incorrect credentials
- Test accessing protected endpoints with/without auth
- Upload a test map (requires auth)
- Verify the uploaded map appears in "My Maps"
- Test token persistence (re-login)
- Test duplicate registration prevention
- Clean up test data

### Manual Testing (Browser)

Follow these steps to manually test the authentication flow:

#### 1. Navigate to Community Portal
Open in browser: `http://localhost:8000/community`

#### 2. Register New User Account
- Click "Register" button
- Fill in registration form:
  - Username: `testuser`
  - Email: `test@example.com`
  - Password: `TestPassword123!`
- Click "Register"
- Verify success message appears
- Verify navigation shows "Welcome, testuser"

#### 3. Verify Login Successful
- Click "Logout" button
- Click "Login" button
- Enter credentials:
  - Username or Email: `testuser`
  - Password: `TestPassword123!`
- Click "Login"
- Verify success message: "Welcome back, testuser!"
- Verify navigation shows "Welcome, testuser"

#### 4. Upload a Map (Requires Authentication)
- Click "Upload" in navigation
- Fill in map details:
  - Name: `Test Map`
  - Description: `A test map for authentication verification`
  - Terrain: `Continental`
  - Size: `1024`
  - Players: `4`
  - Tags: `test, auth` (optional)
- Select a .sd7 map file (create one if needed)
- Click "Upload Map"
- Verify success notification
- Verify navigation returns to browse section
- Verify map appears in grid

#### 5. Logout and Login Again
- Click "Logout" button
- Verify "Login" and "Register" buttons appear
- Click "Login"
- Enter credentials
- Verify successful login

#### 6. Verify Uploaded Map Appears in 'My Maps'
- Click "My Maps" in navigation
- Verify section title shows "My Maps" (not "Community Maps")
- Verify only maps uploaded by current user are shown
- Verify the map uploaded in step 4 appears in the list
- Verify map count matches number of maps you uploaded

## Backend API Endpoints Tested

### POST /api/auth/register
Registers a new user account.

**Request:**
```json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "TestPassword123!"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_active": true,
    "created_at": "2026-01-22T10:00:00Z"
  }
}
```

### POST /api/auth/login
Authenticates a user and returns a JWT token.

**Request:**
```json
{
  "username": "testuser",
  "password": "TestPassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_active": true,
    "created_at": "2026-01-22T10:00:00Z"
  }
}
```

### GET /api/auth/me
Returns the current authenticated user's information.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "is_active": true,
  "created_at": "2026-01-22T10:00:00Z",
  "updated_at": null
}
```

**Response (401 Unauthorized):**
Returned when no token or invalid token provided.

### POST /api/maps/upload
Uploads a new map (requires authentication).

**Request (multipart/form-data):**
- `file`: .sd7 map file
- `name`: Map display name
- `shortname`: Short identifier
- `description`: Map description
- `author`: Map author name
- `version`: Map version
- `generation_params`: JSON string with generation parameters
- `bar_info`: JSON string with BAR-specific info
- `preview_image`: Optional preview image file

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "Test Map",
  "shortname": "test_map",
  "creator_id": 1,
  "creator": {
    "id": 1,
    "username": "testuser"
  },
  ...
}
```

### GET /api/maps?creator_id={user_id}
Lists maps filtered by creator ID (for "My Maps" feature).

**Query Parameters:**
- `creator_id`: User ID to filter by (exact match)
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10, max: 100)

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Test Map",
      "creator_id": 1,
      "creator": {
        "id": 1,
        "username": "testuser"
      },
      ...
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

## Frontend JavaScript Functions Tested

### Authentication State Management
- `loadAuthState()` - Loads token/user from localStorage
- `saveAuthState(token, user)` - Saves token/user to localStorage
- `clearAuthState()` - Clears token/user from localStorage
- `getAuthHeaders()` - Returns Authorization header with Bearer token

### Authentication UI Functions
- `showAuthModal(mode)` - Shows login or registration modal
- `hideAuthModal()` - Hides authentication modal
- `handleAuth(e)` - Handles form submission for login/register
- `switchAuthMode()` - Toggles between login and register forms
- `handleLogout()` - Logs out user and clears state

### Navigation and "My Maps"
- `showSection(section)` - Shows browse, upload, my-maps, or detail section
  - When `my-maps` selected, sets `showingMyMaps = true`
  - Resets pagination to page 1
  - Reloads maps with creator_id filter
- `fetchMapsFromAPI()` - Fetches maps from backend API
  - If `showingMyMaps = true` and `currentUser` exists, adds `creator_id` filter

## Security Features Verified

✓ **Password Hashing:** Passwords are hashed using bcrypt before storage
✓ **JWT Token Authentication:** Stateless token-based authentication
✓ **Token Expiration:** Tokens expire after 7 days (configurable)
✓ **Protected Routes:** Upload and other protected routes require valid token
✓ **Authorization Header:** Tokens sent via `Authorization: Bearer <token>` header
✓ **Duplicate Prevention:** Cannot register with existing username or email
✓ **Credential Validation:** Login fails with incorrect username/password
✓ **Token Validation:** Invalid tokens are rejected (401 Unauthorized)

## Known Limitations

1. **Token Refresh:** No automatic token refresh mechanism (user must re-login after 7 days)
2. **Password Reset:** Password reset functionality not yet implemented
3. **Email Verification:** Email verification not required (would enhance security)
4. **Session Management:** No server-side session invalidation (tokens valid until expiration)
5. **Rate Limiting:** No rate limiting on auth endpoints (would prevent brute force attacks)

## Test Data Cleanup

The test script automatically cleans up:
- Test map file (`test_map.sd7`)
- Temporary token storage
- User IDs and map IDs stored in /tmp

**Note:** Test users remain in the database. For cleanup, manually delete:
```sql
DELETE FROM maps WHERE creator_id IN (SELECT id FROM users WHERE username LIKE 'authtest_%');
DELETE FROM users WHERE username LIKE 'authtest_%';
```

## Troubleshooting

### Server not running
```
Error: Server is not running
Solution: Start the backend server with `cd backend && uvicorn main:app --reload`
```

### Database connection failed
```
Error: Database connection failed
Solution: Start PostgreSQL with `docker-compose up -d db`
```

### Test fails with 401 Unauthorized
```
Error: Expected 200, got HTTP 401
Solution: Verify JWT token is valid and not expired. Check token format.
```

### Map upload fails
```
Error: Upload failed (HTTP 413)
Solution: Verify map file is under 100MB (MAX_UPLOAD_SIZE)
```

### "My Maps" shows all maps
```
Error: My Maps not filtering correctly
Solution: Verify creator_id parameter is being passed to API
```

## Next Steps

Future enhancements to the authentication system:
1. Implement password reset via email
2. Add email verification on registration
3. Implement token refresh mechanism
4. Add rate limiting to auth endpoints
5. Implement OAuth2 social login (Google, GitHub)
6. Add two-factor authentication (2FA)
7. Implement account deletion functionality
