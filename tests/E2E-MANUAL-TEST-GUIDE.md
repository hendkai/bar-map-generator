# End-to-End Manual Test Guide
## Community Map Sharing Portal

This document provides step-by-step instructions for manually testing the complete workflow of the Community Map Sharing Portal.

---

## Prerequisites

### Required Services
1. **Backend API Server** (FastAPI)
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   Expected output: `Application startup complete`

2. **Frontend Community Portal**
   - Open in browser: `http://localhost:8000/community`
   - Or open file: `frontend/community.html`

### Database Setup
- PostgreSQL database must be running (via Docker or locally)
- Database migrations must be applied: `cd backend && alembic upgrade head`

---

## Test Scenario 1: Complete User Journey

### Test Objective
Verify the complete workflow: Generate → Upload → Browse → Search → Download

---

### Step 1: Generate a Map in bar_map_generator.html

**Actions:**
1. Open `bar_map_generator.html` in a browser
2. Verify page loads without console errors
3. Configure map settings:
   - Size: Medium (1024x1024)
   - Terrain Type: Continental
   - Player Count: 4
   - Other settings: defaults or custom values
4. Click "Generate Map" button
5. Wait for generation to complete (progress indicator should show)
6. Verify map preview is displayed in the canvas
7. Verify "Download Complete Package" button is enabled

**Expected Results:**
- ✓ Map generates successfully
- ✓ No console errors
- ✓ Preview image shows terrain visualization
- ✓ Generation completes in reasonable time (< 30 seconds)

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 2: Click 'Share to Community' Button

**Actions:**
1. Locate "🌐 Share to Community" button in button container
2. Click the button
3. Verify a new browser tab opens
4. Verify the new tab loads the community portal

**Expected Results:**
- ✓ Button is visible and clickable
- ✓ New tab opens with URL: `http://localhost:8000/community`
- ✓ Community portal loads without errors
- ✓ Upload form is automatically displayed (not browse section)

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 3: Verify Upload Form is Pre-filled

**Actions:**
1. Check the upload form fields
2. Verify "Map Name" field contains a suggested name
3. Verify "Terrain Type" dropdown matches generator setting
4. Verify "Map Size" dropdown matches generator setting
5. Verify "Player Count" dropdown matches generator setting
6. Verify "Description" field contains auto-generated description
7. Check if preview image is auto-populated

**Expected Results:**
- ✓ All metadata fields are pre-filled with correct values from generator
- ✓ Preview image shows the generated map (if feature implemented)
- ✓ Form is ready for user to review and modify

**Actual Results:**
- [ ] Pass / [ ] Fail

**Notes:**
- Map name should be similar to: "Continental Medium Map"
- Description should mention terrain type and player count
- Preview image should match the canvas from generator

---

### Step 4: Submit the Map to Community Portal

**Actions:**
1. Review all pre-filled fields
2. Modify if desired (or leave as-is)
3. Ensure all required fields are filled:
   - [ ] Map Name
   - [ ] Description
   - [ ] Terrain Type
   - [ ] Map Size
   - [ ] Player Count
4. Select the .sd7 file to upload (from Step 1 download)
5. Optionally select a preview image
6. Click "Upload Map" button
7. Wait for upload to complete

**Expected Results:**
- ✓ Validation passes if all required fields are filled
- ✓ Submit button shows "Uploading..." during upload
- ✓ Success notification appears: "Map uploaded successfully!"
- ✓ Form is cleared after upload
- ✓ Page navigates back to Browse section
- ✓ Uploaded map appears in the map grid

**Actual Results:**
- [ ] Pass / [ ] Fail

**Notes:**
- If not logged in, should show login modal
- .sd7 file must be selected (required field)
- Upload should complete in reasonable time (< 10 seconds for small maps)

---

### Step 5: Browse Community Portal and Find Uploaded Map

**Actions:**
1. Verify you are on the Browse section
2. Scan the map grid for your uploaded map
3. Use pagination if map is not on first page
4. Click on your map to view details

**Expected Results:**
- ✓ Browse section displays map grid
- ✓ Map cards show: preview, name, rating, downloads
- ✓ Your uploaded map appears in the grid
- ✓ Pagination controls work if many maps exist
- ✓ Clicking map card navigates to detail page

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 6: Search for Map by Terrain Type and Size

**Actions:**
1. Locate the search/filter controls
2. Set "Terrain Type" filter to match your map (e.g., "Continental")
3. Set "Map Size" filter to match your map (e.g., "1024")
4. Verify map list updates
5. Verify your uploaded map appears in filtered results

**Expected Results:**
- ✓ Filter controls are visible and functional
- ✓ Map list updates after changing filters
- ✓ Your uploaded map appears in filtered results
- ✓ No unrelated maps appear (filters work correctly)

**Actual Results:**
- [ ] Pass / [ ] Fail

**Additional Tests:**
- Test search by name: Enter part of your map name in search box
- Test sort by: Change "Sort By" dropdown, verify order changes
- Test reset: Click "Reset Filters", verify all filters cleared

---

### Step 7: View Map Details Page

**Actions:**
1. Click on your uploaded map in the grid
2. Verify map detail page loads
3. Check all displayed information:
   - Map name, description, author, version
   - Terrain type, size, player count
   - Preview image
   - Download count
   - Average rating and rating count
   - Upload date

**Expected Results:**
- ✓ Detail page loads without errors
- ✓ All metadata fields display correctly
- ✓ Preview image shows map visualization
- ✓ Download button is visible and clickable
- ✓ Rating stars widget is visible
- ✓ Comments section is visible (even if empty)

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 8: Submit a Rating and Comment

**Actions:**
1. If not logged in, click "Login" and register/login
2. On map detail page, hover over rating stars
3. Click on a star (e.g., 5 stars)
4. Verify success notification appears
5. Verify stars display your rating
6. Scroll to comments section
7. Type a test comment in the textarea
8. Click "Post Comment" button
9. Verify comment appears in the list

**Expected Results:**
- ✓ Rating requires authentication (shows login modal if not logged in)
- ✓ Hover effect highlights stars up to hovered star
- ✓ Clicking star submits rating successfully
- ✓ Success notification: "Rating submitted successfully!"
- ✓ User's rating is displayed (e.g., "You rated this map 5 stars!")
- ✓ Map's average rating updates after rating
- ✓ Comment submission requires authentication
- ✓ Comment appears immediately after posting
- ✓ Comment shows author name, timestamp, and content
- ✓ Comment form is cleared after posting

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 9: Download the Map File

**Actions:**
1. On map detail page, click "Download Map" button
2. Verify browser downloads the .sd7 file
3. Note the download location
4. Refresh the map detail page
5. Check the download count

**Expected Results:**
- ✓ Download button triggers file download
- ✓ Downloaded filename format: `{shortname}_{version}.sd7`
- ✓ File size matches the uploaded file
- ✓ Download count increments by 1 after download

**Actual Results:**
- [ ] Pass / [ ] Fail

**Notes:**
- Before download: Note the download count (e.g., "0 downloads")
- After download: Refresh page and verify count is "1 download"

---

### Step 10: Verify Download Count Incremented

**Actions:**
1. Record download count before download (from Step 9)
2. Download the map
3. Refresh the page or navigate away and back
4. Check the download count again

**Expected Results:**
- ✓ Download count increases by 1 after each download
- ✓ Count persists across page refreshes
- ✓ Count is accurate for all users (not just per-user)

**Actual Results:**
- [ ] Pass / [ ] Fail

**Test Data:**
- Download count before: _______
- Download count after: _______
- Increment verified: [ ] Yes / [ ] No

---

## Test Scenario 2: User Authentication Flow

### Test Objective
Verify user registration, login, and session persistence

---

### Step 1: Register New User

**Actions:**
1. Navigate to community portal
2. Click "Login" button in header
3. In login modal, click "Register" link
4. Fill registration form:
   - Username: unique test username
   - Email: valid email address
   - Password: strong password (> 8 characters)
5. Click "Register" button
6. Verify successful registration

**Expected Results:**
- ✓ Registration form appears when clicking "Register"
- ✓ All fields are validated
- ✓ Success notification: "Registration successful!"
- ✓ User is automatically logged in
- ✓ Header shows welcome message with username
- ✓ Nav menu shows "Logout" button (not "Login")

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 2: Login and Logout

**Actions:**
1. Click "Logout" button
2. Verify logout successful
3. Click "Login" button
4. Enter credentials from Step 1
5. Click "Login" button
6. Verify login successful

**Expected Results:**
- ✓ Logout clears authentication state
- ✓ Header changes to show "Login" button after logout
- ✓ Login form accepts username/email and password
- ✓ Successful login shows welcome message
- ✓ User can access protected routes after login

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 3: Session Persistence

**Actions:**
1. Login to account
2. Close browser tab
3. Open new tab and navigate to community portal
4. Verify still logged in

**Expected Results:**
- ✓ Authentication token stored in localStorage
- ✓ Session persists across browser sessions
- ✓ User remains logged in on page reload
- ✓ Protected routes accessible without re-login

**Actual Results:**
- [ ] Pass / [ ] Fail

---

## Test Scenario 3: Rating and Comment System

### Test Objective
Verify rating and comment functionality with authentication

---

### Step 1: Rate Without Authentication

**Actions:**
1. Logout if logged in
2. Navigate to any map detail page
3. Try to click a rating star

**Expected Results:**
- ✓ Login modal appears when attempting to rate
- ✓ No rating is submitted
- ✓ Clear message: "Please login to rate maps"

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 2: Submit and Update Rating

**Actions:**
1. Login to account
2. Navigate to map detail page
3. Click 5th star (5 stars)
4. Verify rating submitted
5. Click 4th star (4 stars)
6. Verify rating updated

**Expected Results:**
- ✓ First rating creates new rating record
- ✓ Second rating updates existing rating
- ✓ Average rating recalculates after each change
- ✓ Success notifications appear
- ✓ User's current rating is highlighted

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 3: Comment Operations

**Actions:**
1. On map detail page, add a comment
2. Verify comment appears
3. Click "Edit" on your comment
4. Modify comment text and save
5. Verify comment updated
6. Click "Delete" on your comment
7. Confirm deletion
8. Verify comment removed

**Expected Results:**
- ✓ Add comment works with authentication
- ✓ Edit button only shows for own comments
- ✓ Edit form pre-fills with existing text
- ✓ Save updates comment in place
- ✓ Delete button only shows for own comments
- ✓ Confirmation dialog prevents accidental deletion
- ✓ Delete removes comment immediately
- ✓ Other users' comments show author but no edit/delete buttons

**Actual Results:**
- [ ] Pass / [ ] Fail

---

## Test Scenario 4: Error Handling

### Test Objective
Verify proper error handling and user feedback

---

### Step 1: Validation Errors

**Actions:**
1. Try to upload map without required fields
2. Try to upload with invalid file type
3. Try to submit comment without content
4. Try to submit rating out of range (if API allows test)

**Expected Results:**
- ✓ Clear validation messages appear
- ✓ Form does not submit with invalid data
- ✓ Errors are specific and actionable
- ✓ No console errors or crashes

**Actual Results:**
- [ ] Pass / [ ] Fail

---

### Step 2: Network Errors

**Actions:**
1. Stop backend server
2. Try to load maps
3. Try to upload map
4. Try to submit rating

**Expected Results:**
- ✓ Graceful error messages appear
- ✓ No infinite loading states
- ✓ User informed of connection issue
- ✓ Can retry after server restart

**Actual Results:**
- [ ] Pass / [ ] Fail

---

## Test Results Summary

### Automated Test Results
- Test Script: `./tests/e2e-test-workflow.sh`
- Results File: `./test-results/e2e-results-<timestamp>.log`

### Manual Test Results

| Test Scenario | Status | Notes |
|---------------|--------|-------|
| Scenario 1: Complete User Journey | [ ] Pass / [ ] Fail | |
| Scenario 2: User Authentication | [ ] Pass / [ ] Fail | |
| Scenario 3: Ratings and Comments | [ ] Pass / [ ] Fail | |
| Scenario 4: Error Handling | [ ] Pass / [ ] Fail | |

### Overall Status
- [ ] All tests passed
- [ ] Some tests failed (see notes above)

### Issues Found
1.
2.
3.

### Recommendations
1.
2.
3.

---

## Test Execution Checklist

**Pre-Test Setup:**
- [ ] Backend server running on port 8000
- [ ] Database migrations applied
- [ ] Test browser available (Chrome/Firefox/Edge)
- [ ] Browser dev tools open (for console error checking)

**During Testing:**
- [ ] Record actual results for each step
- [ ] Note any deviations from expected results
- [ ] Capture screenshots of failures
- [ ] Check browser console for errors

**Post-Test:**
- [ ] Document all issues found
- [ ] Categorize issues by severity
- [ ] Create GitHub issues for bugs
- [ ] Update test results summary

---

## Additional Notes

**Testing Environment:**
- Browser: _______________
- OS: _______________
- Screen Resolution: _______________
- Date/Time: _______________

**Testers:**
- Primary: _______________
- Reviewer: _______________

**Approval:**
- [ ] Approved for production
- [ ] Approved with minor issues
- [ ] Requires re-testing
- [ ] Failed - critical issues found
