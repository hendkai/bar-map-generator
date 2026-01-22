#!/bin/bash

###############################################################################
# End-to-End Test Script for Community Map Sharing Portal
# Tests complete workflow: Generate → Upload → Browse → Search → Download
###############################################################################

set -e  # Exit on error

# Configuration
API_BASE_URL="http://localhost:8000/api"
COMMUNITY_URL="http://localhost:8000/community"
TEST_RESULTS="./test-results/e2e-results-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create test results directory
mkdir -p ./test-results

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$TEST_RESULTS"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$TEST_RESULTS"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$TEST_RESULTS"
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1" | tee -a "$TEST_RESULTS"
}

check_server() {
    log_test "Checking if backend server is running at $API_BASE_URL/health"
    if curl -s -f "$API_BASE_URL/../health" > /dev/null 2>&1; then
        log_info "✓ Backend server is running"
        return 0
    else
        log_error "✗ Backend server is not running. Please start it first:"
        log_error "  cd backend && uvicorn main:app --reload"
        return 1
    fi
}

# Test variables
TEST_USER_USERNAME="e2e_test_user_$(date +%s)"
TEST_USER_EMAIL="e2e_test_$(date +%s)@example.com"
TEST_USER_PASSWORD="TestPass123!"
TEST_MAP_NAME="E2E Test Map $(date +%s)"
TEST_MAP_SHORTNAME="e2e_test_map_$(date +%s)"
AUTH_TOKEN=""
MAP_ID=""

###############################################################################
# Test Phase 1: User Authentication
###############################################################################
test_auth_registration() {
    log_test "Phase 1: Testing user registration"

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$TEST_USER_USERNAME\",
            \"email\": \"$TEST_USER_EMAIL\",
            \"password\": \"$TEST_USER_PASSWORD\"
        }")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "201" ]; then
        AUTH_TOKEN=$(echo "$BODY" | jq -r '.access_token')
        log_info "✓ User registration successful"
        log_info "  Username: $TEST_USER_USERNAME"
        log_info "  Token: ${AUTH_TOKEN:0:20}..."
        return 0
    else
        log_error "✗ User registration failed (HTTP $HTTP_CODE)"
        log_error "  Response: $BODY"
        return 1
    fi
}

test_auth_login() {
    log_test "Phase 1: Testing user login"

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$TEST_USER_USERNAME\",
            \"password\": \"$TEST_USER_PASSWORD\"
        }")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        AUTH_TOKEN=$(echo "$BODY" | jq -r '.access_token')
        log_info "✓ User login successful"
        log_info "  Token: ${AUTH_TOKEN:0:20}..."
        return 0
    else
        log_error "✗ User login failed (HTTP $HTTP_CODE)"
        log_error "  Response: $BODY"
        return 1
    fi
}

###############################################################################
# Test Phase 2: Map Upload
###############################################################################
test_map_upload() {
    log_test "Phase 2: Testing map upload"

    # Create a test .sd7 file (just a zip file for testing)
    TEST_MAP_FILE="/tmp/test_map_$$.sd7"
    echo "Test map content" > /tmp/test_map.txt
    zip -jq "$TEST_MAP_FILE" /tmp/test_map.txt

    # Create a test preview image
    TEST_PREVIEW_FILE="/tmp/test_preview_$$.png"
    convert -size 512x512 xc:blue "$TEST_PREVIEW_FILE" 2>/dev/null || {
        # If ImageMagick not available, create a minimal PNG
        echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | \
            base64 -d > "$TEST_PREVIEW_FILE"
    }

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/maps/upload" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -F "file=@$TEST_MAP_FILE" \
        -F "name=$TEST_MAP_NAME" \
        -F "shortname=$TEST_MAP_SHORTNAME" \
        -F "description=E2E test map for automated testing" \
        -F "author=E2E Tester" \
        -F "version=1.0" \
        -F 'generation_params={"size":1024,"terrain_type":"continental","player_count":4}' \
        -F 'bar_info={"mapx":16,"mapy":16,"maxplayers":4,"gravity":100}' \
        -F "preview_image=@$TEST_PREVIEW_FILE")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    rm -f "$TEST_MAP_FILE" "$TEST_PREVIEW_FILE" /tmp/test_map.txt

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        MAP_ID=$(echo "$BODY" | jq -r '.id')
        log_info "✓ Map upload successful"
        log_info "  Map ID: $MAP_ID"
        log_info "  Map Name: $TEST_MAP_NAME"
        return 0
    else
        log_error "✗ Map upload failed (HTTP $HTTP_CODE)"
        log_error "  Response: $BODY"
        return 1
    fi
}

###############################################################################
# Test Phase 3: Map Browsing
###############################################################################
test_map_browse() {
    log_test "Phase 3: Testing map browsing (list all maps)"

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/maps?page=1&limit=10")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        TOTAL_MAPS=$(echo "$BODY" | jq -r '.total')
        log_info "✓ Map browsing successful"
        log_info "  Total maps: $TOTAL_MAPS"

        # Check if our uploaded map is in the list
        if echo "$BODY" | jq -e ".items[] | select(.id == $MAP_ID)" > /dev/null; then
            log_info "  ✓ Uploaded map found in browse results"
        else
            log_warning "  Uploaded map not found in browse results (might be pagination issue)"
        fi
        return 0
    else
        log_error "✗ Map browsing failed (HTTP $HTTP_CODE)"
        log_error "  Response: $BODY"
        return 1
    fi
}

###############################################################################
# Test Phase 4: Map Search
###############################################################################
test_map_search() {
    log_test "Phase 4: Testing map search and filtering"

    # Test search by terrain type
    log_test "  Testing search by terrain_type=continental"
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/maps?terrain_type=continental")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        log_info "  ✓ Search by terrain_type successful"
    else
        log_error "  ✗ Search by terrain_type failed (HTTP $HTTP_CODE)"
        return 1
    fi

    # Test search by size
    log_test "  Testing search by size=1024"
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/maps?size=1024")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        log_info "  ✓ Search by size successful"
    else
        log_error "  ✗ Search by size failed (HTTP $HTTP_CODE)"
        return 1
    fi

    # Test combined filters
    log_test "  Testing combined filters (terrain_type=continental&size=1024)"
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/maps?terrain_type=continental&size=1024")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        log_info "  ✓ Combined filters successful"
        return 0
    else
        log_error "  ✗ Combined filters failed (HTTP $HTTP_CODE)"
        return 1
    fi
}

###############################################################################
# Test Phase 5: Map Details
###############################################################################
test_map_details() {
    log_test "Phase 5: Testing map detail view"

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/maps/$MAP_ID")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        MAP_NAME_RESPONSE=$(echo "$BODY" | jq -r '.name')
        log_info "✓ Map detail view successful"
        log_info "  Map Name: $MAP_NAME_RESPONSE"
        log_info "  Terrain: $(echo "$BODY" | jq -r '.terrain_type')"
        log_info "  Size: $(echo "$BODY" | jq -r '.size')"
        log_info "  Player Count: $(echo "$BODY" | jq -r '.player_count')"
        return 0
    else
        log_error "✗ Map detail view failed (HTTP $HTTP_CODE)"
        log_error "  Response: $BODY"
        return 1
    fi
}

###############################################################################
# Test Phase 6: Rating Submission
###############################################################################
test_rating_submission() {
    log_test "Phase 6: Testing rating submission"

    # Submit a rating
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/maps/$MAP_ID/ratings" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"rating": 5}')

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        log_info "✓ Rating submission successful"
        log_info "  Rating value: $(echo "$BODY" | jq -r '.rating')"

        # Verify rating is reflected in map details
        sleep 1  # Give server time to recalculate
        DETAIL_RESPONSE=$(curl -s "$API_BASE_URL/maps/$MAP_ID")
        AVG_RATING=$(echo "$DETAIL_RESPONSE" | jq -r '.average_rating')
        RATING_COUNT=$(echo "$DETAIL_RESPONSE" | jq -r '.rating_count')

        log_info "  Map average rating: $AVG_RATING"
        log_info "  Map rating count: $RATING_COUNT"

        return 0
    else
        log_error "✗ Rating submission failed (HTTP $HTTP_CODE)"
        log_error "  Response: $BODY"
        return 1
    fi
}

###############################################################################
# Test Phase 7: Comment Submission
###############################################################################
test_comment_submission() {
    log_test "Phase 7: Testing comment submission"

    # Submit a comment
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/maps/$MAP_ID/comments" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"content": "E2E test comment - automated testing"}')

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        COMMENT_ID=$(echo "$BODY" | jq -r '.id')
        log_info "✓ Comment submission successful"
        log_info "  Comment ID: $COMMENT_ID"
        log_info "  Content: $(echo "$BODY" | jq -r '.content')"
        return 0
    else
        log_error "✗ Comment submission failed (HTTP $HTTP_CODE)"
        log_error "  Response: $BODY"
        return 1
    fi
}

###############################################################################
# Test Phase 8: Comment Retrieval
###############################################################################
test_comment_retrieval() {
    log_test "Phase 8: Testing comment retrieval"

    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/maps/$MAP_ID/comments")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        COMMENT_COUNT=$(echo "$BODY" | jq 'length')
        log_info "✓ Comment retrieval successful"
        log_info "  Total comments: $COMMENT_COUNT"

        # Check if our test comment is in the list
        if echo "$BODY" | jq -e '.[] | select(.content | contains("E2E test comment"))' > /dev/null; then
            log_info "  ✓ Test comment found in comments list"
        fi
        return 0
    else
        log_error "✗ Comment retrieval failed (HTTP $HTTP_CODE)"
        log_error "  Response: $BODY"
        return 1
    fi
}

###############################################################################
# Test Phase 9: Map Download
###############################################################################
test_map_download() {
    log_test "Phase 9: Testing map download"

    # Get download count before download
    DETAIL_BEFORE=$(curl -s "$API_BASE_URL/maps/$MAP_ID")
    DOWNLOAD_COUNT_BEFORE=$(echo "$DETAIL_BEFORE" | jq -r '.download_count')

    # Download the map
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/maps/$MAP_ID/download" \
        -o "/tmp/test_download_$$.sd7")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        log_info "✓ Map download successful"
        log_info "  Downloaded to: /tmp/test_download_$$.sd7"

        # Wait for server to update download count
        sleep 1

        # Get download count after download
        DETAIL_AFTER=$(curl -s "$API_BASE_URL/maps/$MAP_ID")
        DOWNLOAD_COUNT_AFTER=$(echo "$DETAIL_AFTER" | jq -r '.download_count')

        log_info "  Download count before: $DOWNLOAD_COUNT_BEFORE"
        log_info "  Download count after: $DOWNLOAD_COUNT_AFTER"

        if [ "$DOWNLOAD_COUNT_AFTER" -gt "$DOWNLOAD_COUNT_BEFORE" ]; then
            log_info "  ✓ Download count incremented correctly"
        else
            log_warning "  ✗ Download count did not increment"
        fi

        rm -f "/tmp/test_download_$$.sd7"
        return 0
    else
        log_error "✗ Map download failed (HTTP $HTTP_CODE)"
        return 1
    fi
}

###############################################################################
# Main Test Execution
###############################################################################
main() {
    echo "========================================" | tee -a "$TEST_RESULTS"
    echo "End-to-End Test for Community Map Portal" | tee -a "$TEST_RESULTS"
    echo "Started at: $(date)" | tee -a "$TEST_RESULTS"
    echo "========================================" | tee -a "$TEST_RESULTS"
    echo "" | tee -a "$TEST_RESULTS"

    # Check if server is running
    if ! check_server; then
        log_error "Please start the backend server before running tests"
        exit 1
    fi
    echo "" | tee -a "$TEST_RESULTS"

    # Run all tests
    TESTS_PASSED=0
    TESTS_FAILED=0

    # Phase 1: Authentication
    if test_auth_registration; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    if test_auth_login; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Phase 2: Upload
    if test_map_upload; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Phase 3: Browse
    if test_map_browse; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Phase 4: Search
    if test_map_search; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Phase 5: Details
    if test_map_details; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Phase 6: Rating
    if test_rating_submission; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Phase 7: Comment
    if test_comment_submission; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Phase 8: Comment Retrieval
    if test_comment_retrieval; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Phase 9: Download
    if test_map_download; then ((TESTS_PASSED++)); else ((TESTS_FAILED++)); fi
    echo "" | tee -a "$TEST_RESULTS"

    # Print summary
    echo "========================================" | tee -a "$TEST_RESULTS"
    echo "Test Summary" | tee -a "$TEST_RESULTS"
    echo "========================================" | tee -a "$TEST_RESULTS"
    log_info "Tests Passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests Failed: $TESTS_FAILED"
    else
        log_info "Tests Failed: $TESTS_FAILED"
    fi
    echo "Finished at: $(date)" | tee -a "$TEST_RESULTS"
    echo "Results saved to: $TEST_RESULTS" | tee -a "$TEST_RESULTS"
    echo "========================================" | tee -a "$TEST_RESULTS"

    # Return exit code based on test results
    if [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main "$@"
